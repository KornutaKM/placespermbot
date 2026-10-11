"""Source watch risk flags must remain review-only, with route impacts."""

from copy import deepcopy
from datetime import UTC, datetime

import pytest

from app.catalog import get_catalog, list_catalogs
from app.place_review_queue import (
    build_review_queue,
    priority_for_signal,
    render_markdown,
)
from app.place_source_probe import run_audit


def test_offline_scan_queues_withheld_but_never_promotes_unchanged_urls():
    scan = run_audit(live=False)
    result = build_review_queue(scan)
    assert result["city_count"] == 104
    assert result["active_place_count"] == 2141
    assert result["withheld_count"] == 1
    assert result["tracked_count"] == 2142
    assert len(result["city_summary"]) == 104
    assert result["critical_review_count"] == 0
    assert result["source_identity_review_count"] == 0
    assert result["technical_retry_count"] == 0
    assert result["review_queue_count"] == 0
    assert result["withheld"][0]["place_slug"] == "nalchik-osm-way-234973881"
    assert sum(c["total"] for c in result["city_summary"]) == 2141
    assert sum(c["operator_listings"] for c in result["city_summary"]) == 24
    assert result["official_tourism_listing_count"] == 3
    assert sum(c["official_tourism_listings"] for c in result["city_summary"]) == 3
    assert next(c for c in result["city_summary"] if c["slug"] == "omsk")[
        "official_tourism_listings"
    ] == 3
    assert "Tourism office" in render_markdown(result)
    assert sum(c["not_documented_by_operator"] for c in result["city_summary"]) == (
        result["active_place_count"]
        - sum(c["operator_listings"] for c in result["city_summary"])
    )
    assert sum(c["withheld"] for c in result["city_summary"]) == 1


def test_review_queue_maps_lifecycle_to_routes_without_auto_removal():
    scan = run_audit(live=False)
    nalchik = get_catalog("nalchik")
    place = next(
        p for p in nalchik.places
        if any(p.slug in route.place_slugs for route in nalchik.routes)
    )
    entry = next(
        row for row in scan["places"]
        if row["city_slug"] == "nalchik" and row["place_slug"] == place.slug
    )
    entry["probe"] = {
        "signal": "mapped_inactive_review_required",
        "map_lifecycle": {"construction": "yes"},
    }
    report = build_review_queue(scan)
    assert report["critical_review_count"] == 1
    flagged = report["queue"][0]
    assert flagged["place_slug"] == place.slug
    assert flagged["priority"] == "P0_documentary_investigation"
    assert flagged["route_count"] > 0
    assert flagged["route_slugs"] == sorted(
        route.slug for route in nalchik.routes if place.slug in route.place_slugs
    )
    assert flagged["disposition"].startswith("independent evidence")
    assert nalchik.place_by_slug(place.slug) is not None
    text = render_markdown(report)
    assert "Дворец театров" in text
    assert "104-city source review queue" in text
    assert "mapped_inactive_review_required" in text


def test_blocked_urls_are_retries_not_demolition_and_previous_baseline_supported():
    baseline = run_audit(live=False)
    current = deepcopy(baseline)
    perm = next(
        row for row in current["places"] if row["city_slug"] == "perm"
    )
    perm["probe"] = {"signal": "probe_blocked_or_throttled", "http_status": 403}
    report = build_review_queue(current, previous=baseline)
    assert report["technical_retry_count"] == 1
    assert report["critical_review_count"] == 0
    assert report["new_or_changed_count"] == 1
    assert report["queue"][0]["previous_signal"] == "not_probed"
    assert "do not interpret as closure" in report["queue"][0]["disposition"]
    assert report["city_summary"][0]["slug"] != ""
    assert sum(c["retry"] for c in report["city_summary"]) == 1


def test_unknown_signals_corrupted_urls_and_missing_rows_fail_closed():
    scan = run_audit(live=False)
    with pytest.raises(ValueError, match="exactly once"):
        build_review_queue({**scan, "places": scan["places"][:-1]})

    tampered = deepcopy(scan)
    tampered["places"][0]["source_url"] = "https://fake.example/"
    with pytest.raises(ValueError, match="differs"):
        build_review_queue(tampered)

    tampered = deepcopy(scan)
    tampered["places"][0]["probe"] = {"signal": "verified_open"}
    with pytest.raises(ValueError, match="unknown probe signal"):
        build_review_queue(tampered)

    tampered = deepcopy(scan)
    tampered["withheld_review_watch"] = []
    with pytest.raises(ValueError, match="withheld"):
        build_review_queue(tampered)


def test_priority_categories_and_ranking():
    assert priority_for_signal("mapped_access_restriction_review_required") == (
        "P0_documentary_investigation"
    )
    assert priority_for_signal("map_feature_missing_review_required") == (
        "P1_source_identity_review"
    )
    assert priority_for_signal("probe_inconclusive") == (
        "P2_retry_or_manual_source"
    )
    assert priority_for_signal("source_reachable_not_venue_verified") is None
    report = build_review_queue(run_audit(live=False))
    assert isinstance(report["produced_at"], str)
    assert datetime.fromisoformat(report["produced_at"]).tzinfo == UTC
    assert len(report["city_summary"]) == len(list_catalogs())


def test_same_source_technical_error_recovery_is_not_venue_verification():
    previous = run_audit(live=False)
    current = deepcopy(previous)
    old = next(p for p in previous["places"] if p["source_kind"] == "web")
    now = next(
        p for p in current["places"]
        if (p["city_slug"], p["place_slug"]) ==
        (old["city_slug"], old["place_slug"])
    )
    old["probe"] = {"signal": "probe_inconclusive", "error_type": "URLError"}
    now["probe"] = {"signal": "source_reachable_not_venue_verified",
                    "http_status": 200}
    report = build_review_queue(current, previous=previous)
    assert report["technical_retry_count"] == 0
    assert report["recovered_technical_probe_count"] == 1
    assert report["persistent_technical_retry_count"] == 0
    assert report["source_url_change_count"] == 0
    assert report["same_source_comparable_count"] == 2141
    recovered = report["recovered_technical_probes"][0]
    assert recovered["place_slug"] == now["place_slug"]
    assert recovered["source_url"] == now["source_url"]
    assert recovered["previous_signal"] == "probe_inconclusive"
    assert recovered["current_signal"] == "source_reachable_not_venue_verified"
    assert "NOT verified" in recovered["meaning"]
    assert "technical probes no longer failing: **1**" in render_markdown(report)


def test_source_url_changes_are_not_technical_recoveries():
    previous = run_audit(live=False)
    current = deepcopy(previous)
    old = previous["places"][0]
    now = current["places"][0]
    old["source_url"] = "https://previous-source.example/place"
    old["probe"] = {"signal": "probe_inconclusive"}
    now["probe"] = {"signal": "probe_inconclusive"}
    report = build_review_queue(current, previous=previous)
    assert report["source_url_change_count"] == 1
    assert report["recovered_technical_probe_count"] == 0
    assert report["persistent_technical_retry_count"] == 0
    assert report["same_source_comparable_count"] == 2140
    flagged = report["queue"][0]
    assert flagged["source_changed_since_previous"] is True
    assert flagged["new_or_changed"] is True
    assert report["new_or_changed_count"] == 1
    changed = report["source_url_changes"][0]
    assert changed["previous_url"] == "https://previous-source.example/place"
    assert changed["current_url"] == now["source_url"]


def test_repeated_technical_retry_is_reported_separately():
    previous = run_audit(live=False)
    current = deepcopy(previous)
    old = previous["places"][0]
    now = current["places"][0]
    old["probe"] = {"signal": "probe_blocked_or_throttled", "http_status": 403}
    now["probe"] = {"signal": "probe_inconclusive", "error_type": "URLError"}
    report = build_review_queue(current, previous=previous)
    assert report["persistent_technical_retry_count"] == 1
    assert report["recovered_technical_probe_count"] == 0
    assert report["new_or_changed_count"] == 1
    assert report["queue"][0]["previous_signal"] == "probe_blocked_or_throttled"
    assert report["queue"][0]["source_changed_since_previous"] is False


def test_duplicate_previous_snapshot_does_not_silently_corrupt_transitions():
    previous = run_audit(live=False)
    previous["places"].append(deepcopy(previous["places"][0]))
    with pytest.raises(ValueError, match="Duplicate place in previous scan"):
        build_review_queue(run_audit(live=False), previous=previous)

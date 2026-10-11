"""MVP-135: geodesic OSM node movements and shared source-domain failures."""

from copy import deepcopy
from dataclasses import replace
from urllib.error import HTTPError

from app.catalog import list_catalogs
from app.domain import PlaceSource
from app.place_review_queue import build_review_queue, render_markdown
from app.place_source_probe import (
    NODE_DRIFT_REVIEW_METERS,
    annotate_osm_node_position,
    probe_page,
    run_audit,
)


def osm_node_place():
    for city in list_catalogs():
        for place in city.places:
            if "/node/" in place.source.url:
                return place
    raise AssertionError("Expected at least one node source")


def test_large_node_movement_only_requests_manual_geolocation_review():
    place = osm_node_place()
    old = {
        "signal": "map_feature_present_not_venue_verified",
        "map_lat": str(place.latitude + 0.009),
        "map_lon": str(place.longitude),
    }
    actual = annotate_osm_node_position(place, old)
    assert old["signal"] == "map_feature_present_not_venue_verified"
    assert actual["signal"] == "mapped_coordinates_changed_review_required"
    assert actual["map_position_delta_m"] >= NODE_DRIFT_REVIEW_METERS

    near = annotate_osm_node_position(place, {
        **old, "map_lat": str(place.latitude + 0.001),
    })
    assert near["signal"] == "map_feature_present_not_venue_verified"
    assert near["map_position_delta_m"] < NODE_DRIFT_REVIEW_METERS


def test_invalid_osm_coordinates_and_existing_inactive_flag_are_conservative():
    place = osm_node_place()
    base = {"signal": "map_feature_present_not_venue_verified"}
    assert annotate_osm_node_position(place, base) == base
    assert annotate_osm_node_position(place, {**base, "map_lat": "bad"}) == {
        **base, "map_lat": "bad"
    }
    assert annotate_osm_node_position(place, {
        **base, "map_lat": "nan", "map_lon": "0",
    })["signal"] == "map_feature_present_not_venue_verified"
    assert annotate_osm_node_position(place, {
        **base, "map_lat": "95", "map_lon": "56",
    })["signal"] == "mapped_invalid_coordinates_review_required"
    existing = {
        "signal": "mapped_inactive_review_required",
        "map_lat": "0", "map_lon": "0",
    }
    assert annotate_osm_node_position(place, existing) == existing
    non_node = replace(
        place,
        source=PlaceSource(
            place.source.name,
            "https://www.openstreetmap.org/way/123",
            place.source.checked_at,
        ),
    )
    assert annotate_osm_node_position(non_node, {
        **base, "map_lat": "0", "map_lon": "0",
    })["signal"] == "map_feature_present_not_venue_verified"


def test_route_aware_queue_marks_coordinate_drift_as_p1_not_demolition():
    scan = run_audit(live=False)
    city_place = next(
        (c, p) for c in list_catalogs() for p in c.places
        if "/node/" in p.source.url
        and any(p.slug in route.place_slugs for route in c.routes)
    )
    city, place = city_place
    row = next(
        entry for entry in scan["places"]
        if entry["city_slug"] == city.slug and entry["place_slug"] == place.slug
    )
    row["probe"] = {
        "signal": "mapped_coordinates_changed_review_required",
        "map_position_delta_m": 720,
    }
    report = build_review_queue(scan)
    assert report["location_review_count"] == 1
    assert report["critical_review_count"] == 0
    assert report["source_identity_review_count"] == 0
    q = report["queue"][0]
    assert q["priority"] == "P1_location_review"
    assert q["route_count"] > 0
    assert "do not assume" in q["disposition"]
    assert any(
        c["slug"] == city.slug and c["location_review"] == 1
        for c in report["city_summary"]
    )


def test_repeated_http_errors_cluster_at_domain_not_attraction_level():
    scan = run_audit(live=False)
    rows = [
        row for row in scan["places"]
        if row["source_url"].startswith("https://www.culture.ru/")
    ]
    assert len(rows) >= 2
    rows[0]["probe"] = {
        "signal": "probe_inconclusive", "error_type": "URLError",
    }
    rows[1]["probe"] = {
        "signal": "probe_blocked_or_throttled", "http_status": 403,
    }
    report = build_review_queue(scan)
    assert report["technical_retry_count"] == 2
    assert report["technical_retry_host_count"] == 1
    host = report["technical_retry_hosts"][0]
    assert host["host"] == "culture.ru"
    assert host["affected_places"] == 2
    assert host["affected_city_count"] >= 1
    assert host["error_types"] == {"URLError": 1}
    assert host["http_statuses"] == {"403": 1}
    assert host["affected_route_count"] >= 0
    assert "Do not" in host["resolution"]
    assert "Technical retry clusters by source host" in render_markdown(report)


def test_host_dedupes_www_and_no_www_source_links():
    scan = run_audit(live=False)
    candidates = [
        row for row in scan["places"]
        if row["source_url"].startswith("https://www.world-ocean.ru/")
        or row["source_url"].startswith("https://world-ocean.ru/")
    ]
    assert len(candidates) >= 2
    for row in candidates[:2]:
        row["probe"] = {
            "signal": "probe_inconclusive", "error_type": "URLError",
        }
    summary = build_review_queue(scan)["technical_retry_hosts"]
    assert summary[0]["host"] == "world-ocean.ru"
    assert summary[0]["affected_places"] == 2


def test_head_403_retries_once_as_get_and_does_not_certify_venue(monkeypatch):
    from app import place_source_probe

    methods = []

    def fake_http(url, *, timeout, method="GET"):
        methods.append(method)
        if method == "HEAD":
            raise HTTPError(url, 403, "HEAD blocked", {}, None)
        return (200, url, b"<html>Page present only</html>")

    monkeypatch.setattr(place_source_probe, "http_request", fake_http)
    result = probe_page("https://example.org/museum")
    assert methods == ["HEAD", "GET"]
    assert result["signal"] == "source_reachable_not_venue_verified"
    assert result["probe_method"] == "GET"


def test_head_429_does_not_retry_and_stays_technical_failure(monkeypatch):
    from app import place_source_probe

    methods = []

    def fake_http(url, *, timeout, method="GET"):
        methods.append(method)
        raise HTTPError(url, 429, "Rate limited", {}, None)

    monkeypatch.setattr(place_source_probe, "http_request", fake_http)
    result = probe_page("https://example.org/")
    assert methods == ["HEAD"]
    assert result["signal"] == "probe_blocked_or_throttled"
    assert result["probe_method"] == "HEAD"


def test_previous_signals_remain_comparable_and_offline_without_network():
    baseline = run_audit(live=False)
    current = deepcopy(baseline)
    current["places"][0]["probe"] = {
        "signal": "mapped_coordinates_changed_review_required"
    }
    result = build_review_queue(current, previous=baseline)
    assert result["new_or_changed_count"] == 1
    assert result["review_queue_count"] == 1
    assert result["location_review_count"] == 1

"""Documentary evidence and conservative external-source drift detection."""

from dataclasses import replace
from datetime import date

from app.catalog import get_catalog, list_catalogs
from app.place_evidence import EVIDENCE, public_evidence, validate_evidence
from app.place_freshness import build_inventory
from app.place_source_probe import (
    classify_url,
    osm_lifecycle_signal,
    probe_osm_batch,
    probe_page,
    probe_wikidata,
    run_audit,
)


def test_all_documentary_evidence_points_exist_and_sources_are_independent():
    assert len(EVIDENCE) == 16
    assert sum(item.city_slug == "perm" for item in EVIDENCE) == 14
    assert validate_evidence(as_of=date(2026, 10, 11)) == ()
    assert {
        "perm-art-gallery", "perm-zoo", "permm",
        "perm-childrens-museum-center", "perm-antiquities-museum",
    } <= {item.place_slug for item in EVIDENCE}
    assert len({(e.city_slug, e.place_slug) for e in EVIDENCE}) == 16


def test_evidence_is_a_operator_listing_not_guaranteed_access():
    listed = public_evidence(
        "perm", "perm-childrens-museum-center",
        as_of=date(2026, 10, 11),
    )
    assert listed["status"] == "operator_listed"
    assert "https://museumperm.ru/branch/kids" == listed["evidence_url"]
    assert "Советской, 1" in listed["finding"]
    unknown = public_evidence("perm", "perm-station-garden",
                              as_of=date(2026, 10, 11))
    assert unknown["status"] == "not_independently_checked"
    assert unknown["evidence_url"] is None
    assert public_evidence(
        "perm", "perm-zoo", as_of=date(2027, 2, 1)
    )["status"] == "evidence_stale"


def test_evidence_validation_catches_missing_place_in_altered_catalog():
    perm = get_catalog("perm")
    altered = replace(perm, places=tuple(
        p for p in perm.places if p.slug != "perm-zoo"
    ))
    bad = validate_evidence((altered,), as_of=date(2026, 10, 11))
    assert any("perm-zoo" in item for item in bad)


def test_all_city_inventory_annotates_every_source_without_false_claims():
    report = build_inventory(as_of=date(2026, 10, 11))
    assert report["active_places_count"] == 2141
    assert report["documented_operator_listings"] == 16
    assert report["blocking_findings"] == []
    checked = [
        p for p in report["places"]
        if p["documentary_evidence"]["status"] == "operator_listed"
    ]
    assert len(checked) == 16
    assert {p["city_slug"] for p in checked} == {"perm", "yaroslavl", "volgograd"}
    assert all(p["review_status"] == "requires_current_independent_confirmation"
               for p in report["places"])


def test_source_probe_classification_and_no_network_structural_coverage():
    assert classify_url("https://www.openstreetmap.org/node/123") == (
        "osm", "node", "123"
    )
    assert classify_url("https://www.wikidata.org/wiki/Q314") == (
        "wikidata", "entity", "Q314"
    )
    assert classify_url("https://museumperm.ru/visit")[0] == "web"
    report = run_audit(live=False)
    assert report["city_count"] == len(list_catalogs()) == 104
    assert report["place_count"] == 2141
    assert len(report["places"]) == 2141
    assert report["signal_counts"] == {"not_probed": 2141}
    assert report["total_tracked"] == 2142
    assert report["withheld_count"] == 1
    assert report["withheld_review_watch"][0]["place_slug"] == (
        "nalchik-osm-way-234973881"
    )
    assert {p["city_slug"] for p in report["places"]} == {
        c.slug for c in list_catalogs()
    }
    assert all(p["reality_status"] == "not_proven_by_automated_source_probe"
               for p in report["places"])


def test_osm_access_and_lifecycle_tags_are_only_review_signals():
    assert osm_lifecycle_signal({"historic": "memorial"}) == (
        "map_feature_present_not_venue_verified"
    )
    assert osm_lifecycle_signal({"disused:tourism": "museum"}) == (
        "mapped_inactive_review_required"
    )
    assert osm_lifecycle_signal({"access": "private"}) == (
        "mapped_access_restriction_review_required"
    )
    assert osm_lifecycle_signal({"demolished:building": "yes"}) == (
        "mapped_inactive_review_required"
    )


def test_source_probe_osm_batch_parses_entities_not_merely_url_ok(monkeypatch):
    from app import place_source_probe

    def fake_http(url, *, timeout, method="GET"):
        assert "/nodes?nodes=" in url
        assert method == "GET"
        return (200, url,
                (b'<osm><node id="1" lat="58.0" lon="56.0" '
                 b'timestamp="2026-08-01T00:00:00Z">'
                 b'<tag k="name" v="Example"/>'
                 b'</node></osm>'))

    monkeypatch.setattr(place_source_probe, "http_request", fake_http)
    result = probe_osm_batch("node", ["1", "2"])
    assert result["1"]["map_name"] == "Example"
    assert result["1"]["signal"] == "map_feature_present_not_venue_verified"
    assert result["2"]["signal"] == "map_feature_missing_review_required"


def test_source_probe_wikidata_marks_dissolution_only_for_review(monkeypatch):
    from app import place_source_probe

    def fake_http(url, *, timeout, method="GET"):
        assert "wbgetentities" in url
        return (200, url, (b'{"entities":{"Q1":{"claims":{"P576":[{}]},'
                            b'"lastrevid":20},"Q2":{"claims":{},"lastrevid":30}}}'))

    monkeypatch.setattr(place_source_probe, "http_request", fake_http)
    result = probe_wikidata(["Q1", "Q2"])
    assert result["Q1"]["signal"] == "wikidata_end_date_review_required"
    assert result["Q2"]["signal"] == "wikidata_item_present_not_venue_verified"


def test_http_error_not_proof_of_attraction_closed(monkeypatch):
    from urllib.error import HTTPError

    from app import place_source_probe

    def fake_http(url, *, timeout, method="GET"):
        raise HTTPError(url, 403, "Forbidden", {}, None)

    monkeypatch.setattr(place_source_probe, "http_request", fake_http)
    result = probe_page("https://example.com/", timeout=1)
    assert result["signal"] == "probe_blocked_or_throttled"
    assert result["http_status"] == 403

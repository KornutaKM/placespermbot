"""All 104 cities are inventoried without conflating source dates with open status."""

from dataclasses import replace
from datetime import date

from app.catalog import get_catalog, list_catalogs
from app.place_freshness import (
    OBSERVATIONS,
    RETIRED,
    build_inventory,
    check_retirements,
    render_markdown,
    source_type,
)


def test_demolished_perm_gates_never_reappear_in_a_live_city_or_route():
    catalogs = list_catalogs()
    assert len(catalogs) == 104
    assert check_retirements(catalogs) == ()
    perm = get_catalog("perm")
    assert perm.place_by_slug("perm-gates") is None
    assert len(perm.places) == 31
    assert len(perm.routes) == 14
    assert all("perm-gates" not in r.place_slugs for r in perm.routes)
    assert perm.route_by_slug("perm-railway-garden") is None
    new_route = perm.route_by_slug("perm-esplanade-memory")
    assert new_route is not None
    assert new_route.place_slugs == (
        "perm-esplanade-family", "front-and-rear-monument"
    )
    garden = perm.place_by_slug("perm-station-garden")
    assert garden is not None
    assert "демонтирован" in garden.summary


def test_confirmed_retirement_has_multiple_independent_sources():
    assert len(RETIRED) == 1
    retired = RETIRED[0]
    assert retired.city_slug == "perm"
    assert retired.place_slug == "perm-gates"
    assert retired.event_date == "2024-06-19"
    assert len(retired.sources) == 3
    assert all(url.startswith("https://") for url in retired.sources)


def test_retired_slug_guard_rejects_accidental_catalog_restoration():
    perm = get_catalog("perm")
    bogus = replace(perm.places[0], slug="perm-gates")
    fake_city = replace(perm, places=(*perm.places, bogus))
    findings = check_retirements((fake_city,))
    assert len(findings) == 1
    assert "removed object is active" in findings[0]

    stale_route = replace(
        perm.routes[0],
        place_slugs=(*perm.routes[0].place_slugs, "perm-gates"),
    )
    fake_city = replace(perm, routes=(*perm.routes, stale_route))
    findings = check_retirements((fake_city,))
    assert any("visits removed" in line for line in findings)


def test_freshness_inventory_works_for_every_active_city_and_source():
    report = build_inventory(as_of=date(2026, 10, 12))
    assert report["cities_count"] == 104
    assert report["active_places_count"] == 2141
    assert report["not_verified_now"] == report["active_places_count"]
    assert len(report["cities"]) == 104
    assert len(report["places"]) == 2141
    assert len({c["slug"] for c in report["cities"]}) == 104
    assert {p["city_slug"] for p in report["places"]} == {
        c["slug"] for c in report["cities"]
    }
    assert sum(report["source_types"].values()) == report["active_places_count"]
    assert report["source_types"]["community_osm"] >= 58 * 18 - 1
    assert report["source_types"]["community_wikidata"] >= 18
    assert report["blocking_findings"] == []
    assert report["historically_removed_count"] == 1
    assert report["withheld_pending_review_count"] == 1
    assert report["withheld_pending_review"][0]["place_slug"] == (
        "nalchik-osm-way-234973881"
    )
    assert report["documented_past_observations"] == 3
    assert all(
        p["review_status"] == "requires_current_independent_confirmation"
        for p in report["places"]
    )
    assert all(p["source_url"].startswith("https://") for p in report["places"])
    assert "perm-gates" not in {p["place_slug"] for p in report["places"]}


def test_gallery_report_is_a_dated_observation_not_current_access_guarantee():
    assert OBSERVATIONS[0].reported_on == "2026-04-02"
    report = build_inventory(as_of=date(2026, 10, 11))
    gallery = next(
        p for p in report["places"]
        if p["city_slug"] == "perm" and p["place_slug"] == "perm-art-gallery"
    )
    assert gallery["past_published_observation"]["reported_on"] == "2026-04-02"
    assert gallery["review_status"] == "requires_current_independent_confirmation"
    rendered = render_markdown(report)
    assert "104" in rendered and "2141" in rendered
    assert "Пермские ворота" in rendered
    assert "перев" not in gallery["review_status"]


def test_source_categories_do_not_imply_place_exists_today():
    assert source_type("https://www.openstreetmap.org/node/123") == "community_osm"
    assert source_type("https://www.wikidata.org/wiki/Q12") == "community_wikidata"
    assert source_type("https://museumperm.ru/branches") == "editorial_or_institutional"

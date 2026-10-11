"""A construction signal is never proof of demolition or visitor access."""

from dataclasses import replace

from app.catalog import get_catalog, list_catalogs
from app.withheld_places import WITHHELD_PLACES, check_withheld


def test_nalchik_construction_feature_is_not_a_recommended_place_or_route():
    assert len(WITHHELD_PLACES) == 1
    withheld = WITHHELD_PLACES[0]
    assert withheld.city_slug == "nalchik"
    assert withheld.place_slug == "nalchik-osm-way-234973881"
    assert withheld.map_last_modified.startswith("2026-03-15")
    assert "construction=yes" in withheld.reason
    city = get_catalog("nalchik")
    assert len(city.places) == 17
    assert len(city.routes) == 5
    assert city.place_by_slug(withheld.place_slug) is None
    assert all(withheld.place_slug not in route.place_slugs for route in city.routes)
    assert check_withheld(list_catalogs()) == ()


def test_withheld_guard_blocks_accidental_repulication():
    city = get_catalog("nalchik")
    removed_slug = WITHHELD_PLACES[0].place_slug
    with_place = replace(city, places=(
        *city.places, replace(city.places[0], slug=removed_slug)
    ))
    assert any("construction site active" in issue
               for issue in check_withheld((with_place,)))
    with_route = replace(city, routes=(
        *city.routes,
        replace(city.routes[0], place_slugs=(
            *city.routes[0].place_slugs, removed_slug,
        )),
    ))
    assert any("route contains withheld site" in issue
               for issue in check_withheld((with_route,)))

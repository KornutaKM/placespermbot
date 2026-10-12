"""A fishing-industry museum in a village must never be mapped to Astrakhan city."""

from dataclasses import replace
from datetime import date

from app.catalog import get_catalog
from app.place_freshness import (
    CORRECTED_MISLOCATIONS,
    build_inventory,
    check_retirements,
)


def test_city_history_museum_replaces_wrong_fishing_museum_coordinate():
    city = get_catalog("astrakhan")
    assert len(city.places) == 12
    assert len(city.routes) == 5
    assert city.place_by_slug("astrakhan-aquarium") is None
    museum = city.place_by_slug("astrakhan-history-city")
    assert museum is not None
    assert museum.title == "Музей истории города Астрахани"
    assert museum.category == "museums"
    assert museum.district == "Ульяновых, 9"
    assert museum.source.checked_at == date(2026, 10, 11)
    assert museum.source.url == (
        "https://www.culture.ru/institutes/20501/"
        "muzei-istorii-goroda-astrakhani"
    )
    assert abs(museum.latitude - 46.35212) < 0.00001
    assert abs(museum.longitude - 48.03163) < 0.00001
    assert all("astrakhan-aquarium" not in route.place_slugs
               for route in city.routes)
    assert any("astrakhan-history-city" in route.place_slugs
               for route in city.routes)
    assert "Музей истории рыболовства" not in {
        p.title for p in city.places
    }


def test_mislocated_slug_has_a_separate_non_demolition_tombstone():
    assert len(CORRECTED_MISLOCATIONS) == 1
    entry = CORRECTED_MISLOCATIONS[0]
    assert entry.city_slug == "astrakhan"
    assert entry.old_place_slug == "astrakhan-aquarium"
    assert len(entry.evidence_urls) == 3
    assert "сёлах" in entry.reason
    astrakhan = get_catalog("astrakhan")
    assert check_retirements((astrakhan,)) == ()
    restored = replace(
        astrakhan,
        places=(*astrakhan.places,
                replace(astrakhan.places[0], slug=entry.old_place_slug)),
    )
    assert any("known false city location" in x
               for x in check_retirements((restored,)))
    broken_route = replace(
        astrakhan.routes[0],
        place_slugs=(*astrakhan.routes[0].place_slugs, entry.old_place_slug),
    )
    wrong = replace(astrakhan, routes=(*astrakhan.routes, broken_route))
    assert any("visits mislocated" in x for x in check_retirements((wrong,)))


def test_full_inventory_documents_geographical_correction_without_false_closure():
    report = build_inventory(as_of=date(2026, 10, 12))
    assert report["cities_count"] == 104
    assert report["active_places_count"] == 2141
    assert report["historically_removed_count"] == 1
    assert report["corrected_mislocations_count"] == 1
    assert report["blocking_findings"] == []
    assert report["corrected_mislocations"][0]["old_place_slug"] == (
        "astrakhan-aquarium"
    )
    new = next(
        row for row in report["places"]
        if row["city_slug"] == "astrakhan"
        and row["place_slug"] == "astrakhan-history-city"
    )
    assert new["review_status"] == "requires_current_independent_confirmation"

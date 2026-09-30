from urllib.parse import urlparse

import pytest

from app.catalog import get_catalog, list_catalogs
from app.config import Settings
from app.events import get_event_providers
from app.excursions import get_excursion_providers
from app.personal_route import build_personal_route
from app.planner import INTEREST_LABELS, build_route
from app.recommendations import recommend_personalized

CITY_SLUG = "perm"


def catalog():
    return get_catalog(CITY_SLUG)


def test_perm_is_registered_as_second_city() -> None:
    city = catalog()
    assert city.slug == "perm"
    assert city.name == "Пермь"
    assert {item.slug for item in list_catalogs()} >= {
        "perm",
        "saint-petersburg",
    }


def test_perm_catalog_has_verified_seed_and_unique_ids() -> None:
    city = catalog()
    assert len(city.places) == 8

    slugs = [place.slug for place in city.places]
    assert len(slugs) == len(set(slugs))

    for place in city.places:
        assert place.title.strip()
        assert place.summary.strip()
        assert place.visit_minutes > 0
        assert place.district.strip()
        assert 57.9 <= place.latitude <= 58.1
        assert 56.1 <= place.longitude <= 56.3
        assert place.source.checked_at.isoformat() == "2026-09-30"

        source_url = urlparse(place.source.url)
        assert source_url.scheme == "https"
        assert source_url.hostname


def test_perm_routes_reference_existing_places() -> None:
    city = catalog()
    assert len(city.routes) >= 2

    for route in city.routes:
        assert route.place_slugs
        assert route.duration_minutes > 0
        assert route.distance_km > 0
        for slug in route.place_slugs:
            assert city.place_by_slug(slug) is not None


def test_perm_search_and_categories_use_generic_catalog_logic() -> None:
    city = catalog()

    assert city.search_places("солёные уши")[0].slug == "permyak-salty-ears"
    assert city.search_places("ПАЛЕОНТОЛОГИЯ")[0].slug == "perm-antiquities-museum"

    family = {place.slug for place in city.places_for_category("family")}
    assert "perm-antiquities-museum" in family
    assert "gorky-park-perm" in family

    free = city.places_for_category("free")
    assert free
    assert all(place.is_free for place in free)


def test_perm_nearby_is_distance_sorted() -> None:
    city = catalog()
    nearby = city.nearby_places("perm-bear", radius_km=3.0, limit=5)

    assert nearby
    assert all(place.slug != "perm-bear" for place, _ in nearby)
    distances = [distance for _, distance in nearby]
    assert distances == sorted(distances)


@pytest.mark.parametrize("budget_minutes", [120, 240, 360])
@pytest.mark.parametrize("interest", tuple(INTEREST_LABELS))
def test_perm_generated_routes_stay_within_budget(
    budget_minutes: int,
    interest: str,
) -> None:
    route = build_route(
        catalog(),
        budget_minutes=budget_minutes,
        interest=interest,
    )

    assert route is not None
    assert route.places
    assert route.estimated_minutes <= budget_minutes


def test_perm_personal_recommendations_and_route_are_generic() -> None:
    city = catalog()
    recommendations = recommend_personalized(
        city,
        ("unusual", "free"),
        limit=len(city.places),
        favorite_slugs={"perm-bear"},
        exclude_slugs={"permyak-salty-ears"},
    )

    assert recommendations
    assert recommendations[0].place.slug == "perm-bear"
    assert "permyak-salty-ears" not in {
        item.place.slug
        for item in recommendations
    }

    route = build_personal_route(
        city,
        ("unusual", "free"),
        budget_minutes=240,
        favorite_slugs={"perm-bear"},
        dismissed_slugs={"permyak-salty-ears"},
    )
    assert route is not None
    assert route.estimated_minutes <= route.budget_minutes
    assert "permyak-salty-ears" not in {
        place.slug
        for place in route.places
    }


def test_perm_live_dynamic_providers_fail_closed() -> None:
    settings = Settings()
    assert get_excursion_providers(settings, city_slug=CITY_SLUG) == ()
    assert get_event_providers(settings, city_slug=CITY_SLUG) == ()


def test_classic_interest_label_is_city_neutral() -> None:
    assert INTEREST_LABELS["classic"] == "🏛 Главные места"

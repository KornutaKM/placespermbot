from app.catalog import get_catalog
from app.data.spb import CITY_SLUG


def catalog():
    return get_catalog(CITY_SLUG)


def test_city_is_saint_petersburg() -> None:
    city = catalog()
    assert city.slug == "saint-petersburg"
    assert city.name == "Санкт-Петербург"


def test_place_slugs_are_unique() -> None:
    city = catalog()
    slugs = [place.slug for place in city.places]
    assert len(slugs) == len(set(slugs))


def test_route_references_existing_places() -> None:
    city = catalog()
    for route in city.routes:
        assert route.place_slugs
        for slug in route.place_slugs:
            assert city.place_by_slug(slug) is not None


def test_free_collection_contains_only_free_places() -> None:
    free_places = catalog().places_for_category("free")
    assert free_places
    assert all(place.is_free for place in free_places)


def test_each_place_has_minimum_card_content_and_valid_coordinates() -> None:
    city = catalog()
    for place in city.places:
        assert place.title.strip()
        assert place.summary.strip()
        assert place.visit_minutes > 0
        assert place.district.strip()
        assert -90 <= place.latitude <= 90
        assert -180 <= place.longitude <= 180


def test_nearby_places_excludes_origin_and_is_distance_sorted() -> None:
    city = catalog()
    nearby = city.nearby_places("palace-square", radius_km=5.0)

    assert nearby
    assert all(place.slug != "palace-square" for place, _ in nearby)

    distances = [distance for _, distance in nearby]
    assert distances == sorted(distances)


def test_unknown_city_fails_closed() -> None:
    try:
        get_catalog("unknown-city")
    except RuntimeError as exc:
        assert "Unsupported city" in str(exc)
    else:
        raise AssertionError("Unknown city must fail closed")

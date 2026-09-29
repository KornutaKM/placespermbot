from app.catalog import get_catalog
from app.data.spb import CITY_SLUG


def catalog():
    return get_catalog(CITY_SLUG)


def test_city_is_saint_petersburg() -> None:
    city = catalog()
    assert city.slug == "saint-petersburg"
    assert city.name == "Санкт-Петербург"


def test_catalog_has_useful_seed_size() -> None:
    assert len(catalog().places) >= 14


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


def test_family_collection_uses_family_tags() -> None:
    family_places = catalog().places_for_category("family")
    assert family_places
    assert all("с детьми" in place.tags for place in family_places)


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


def test_search_finds_place_by_name() -> None:
    results = catalog().search_places("эрмитаж")
    assert results
    assert results[0].slug == "hermitage"


def test_search_finds_places_by_tag() -> None:
    results = catalog().search_places("музей")
    slugs = {place.slug for place in results}
    assert "hermitage" in slugs
    assert "russian-museum" in slugs
    assert "kunstkammer" in slugs


def test_search_is_case_insensitive() -> None:
    results = catalog().search_places("АРХИТЕКТУРА")
    assert results


def test_blank_search_returns_nothing() -> None:
    assert catalog().search_places("   ") == ()


def test_unknown_city_fails_closed() -> None:
    try:
        get_catalog("unknown-city")
    except RuntimeError as exc:
        assert "Unsupported city" in str(exc)
    else:
        raise AssertionError("Unknown city must fail closed")


def test_nearby_from_coordinates_is_sorted_and_limited() -> None:
    city = catalog()
    palace = city.place_by_slug("palace-square")
    assert palace is not None

    nearby = city.nearby_from_coordinates(
        palace.latitude,
        palace.longitude,
        radius_km=10.0,
        limit=3,
    )

    assert len(nearby) == 3
    distances = [distance for _, distance in nearby]
    assert distances == sorted(distances)
    assert distances[0] == 0
    assert all(distance <= 10.0 for distance in distances)


def test_nearby_from_coordinates_far_from_city_is_empty() -> None:
    nearby = catalog().nearby_from_coordinates(
        55.7558,
        37.6176,
        radius_km=10.0,
    )

    assert nearby == ()


def test_nearby_from_coordinates_rejects_nonpositive_window() -> None:
    city = catalog()
    place = city.places[0]

    assert city.nearby_from_coordinates(
        place.latitude,
        place.longitude,
        radius_km=0,
    ) == ()
    assert city.nearby_from_coordinates(
        place.latitude,
        place.longitude,
        limit=0,
    ) == ()

from app.data.spb import CITY_SLUG, PLACES, ROUTES, place_by_slug, places_for_category


def test_city_is_saint_petersburg() -> None:
    assert CITY_SLUG == "saint-petersburg"


def test_place_slugs_are_unique() -> None:
    slugs = [place.slug for place in PLACES]
    assert len(slugs) == len(set(slugs))


def test_route_references_existing_places() -> None:
    for route in ROUTES:
        assert route.place_slugs
        for slug in route.place_slugs:
            assert place_by_slug(slug) is not None


def test_free_collection_contains_only_free_places() -> None:
    free_places = places_for_category("free")
    assert free_places
    assert all(place.is_free for place in free_places)


def test_each_place_has_minimum_card_content() -> None:
    for place in PLACES:
        assert place.title.strip()
        assert place.summary.strip()
        assert place.visit_minutes > 0
        assert place.district.strip()

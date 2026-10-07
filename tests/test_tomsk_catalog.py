from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog

CITY_SLUG = "tomsk"


def catalog():
    return get_catalog(CITY_SLUG)


def test_tomsk_catalog_has_current_local_provenance() -> None:
    city = catalog()
    assert len(city.places) >= 23

    for place in city.places:
        assert 56.43 <= place.latitude <= 56.52
        assert 84.92 <= place.longitude <= 84.99
        assert place.source.checked_at == date(2026, 10, 7)
        source = urlparse(place.source.url)
        assert source.scheme == "https"
        assert source.hostname


def test_tomsk_landmarks_use_specific_sources() -> None:
    city = catalog()
    expected_hosts = {
        "tomsk-history-museum": "mit-tomsk.ru",
        "wood-architecture-museum-tomsk": "artmuseumtomsk.ru",
        "tomsk-local-history-museum": "tomskmuseum.ru",
        "tomsk-art-museum": "artmuseumtomsk.ru",
        "tomsk-planetarium": "planetarium.tomsk.ru",
        "siberian-botanical-garden": "sbg.tsu.ru",
        "professor-apartment-tomsk": "museum.tomsk.ru",
    }

    for slug, expected_host in expected_hosts.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert urlparse(place.source.url).hostname == expected_host


def test_tomsk_search_and_virtual_categories() -> None:
    city = catalog()

    assert city.search_places("жар-птицами")[0].slug == "firebird-house-tomsk"
    assert city.search_places("Чехову")[0].slug == "chekhov-monument-tomsk"

    family = {place.slug for place in city.places_for_category("family")}
    assert {
        "tomsk-planetarium",
        "siberian-botanical-garden",
        "university-grove-tomsk",
        "white-lake-tomsk",
        "happiness-monument-tomsk",
    } <= family

    free = city.places_for_category("free")
    assert len(free) >= 15
    assert all(place.is_free for place in free)


def test_tomsk_routes_cover_wooden_university_museums_and_old_city() -> None:
    city = catalog()
    routes = {route.slug: route for route in city.routes}

    assert {
        "tomsk-first-walk",
        "tomsk-wooden",
        "tomsk-museums",
        "tomsk-university",
        "tomsk-old-city",
    } <= routes.keys()
    assert "wood-architecture-museum-tomsk" in routes["tomsk-wooden"].place_slugs
    assert "siberian-botanical-garden" in routes["tomsk-university"].place_slugs
    assert "tomsk-history-museum" in routes["tomsk-old-city"].place_slugs


def test_tomsk_seed_uses_current_2026_museum_sources() -> None:
    city = catalog()

    assert city.place_by_slug("wood-architecture-museum-tomsk") is not None
    assert city.place_by_slug("tomsk-planetarium") is not None
    assert city.place_by_slug("tomsk-art-museum") is not None

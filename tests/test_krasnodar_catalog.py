from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog

CITY_SLUG = "krasnodar"


def catalog():
    return get_catalog(CITY_SLUG)


def test_krasnodar_catalog_has_current_local_provenance() -> None:
    city = catalog()
    assert len(city.places) >= 22

    for place in city.places:
        assert 44.98 <= place.latitude <= 45.08
        assert 38.90 <= place.longitude <= 39.08
        assert place.source.checked_at == date(2026, 10, 6)
        source = urlparse(place.source.url)
        assert source.scheme == "https"
        assert source.hostname


def test_krasnodar_landmarks_use_specific_sources() -> None:
    city = catalog()
    expected_hosts = {
        "felitsyn-museum-krasnodar": "felicina.ru",
        "kovalenko-art-museum": "kovalenkomuseum.ru",
        "krasnodar-park": "www.parkkrasnodar.com",
        "kosenko-botanical-garden": "www.kubsau.ru",
        "weapons-of-victory-museum": "tourism.krd.ru",
    }

    for slug, expected_host in expected_hosts.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert urlparse(place.source.url).hostname == expected_host


def test_krasnodar_search_and_virtual_categories() -> None:
    city = catalog()

    assert city.search_places("Шуховская")[0].slug == "shukhov-tower-krasnodar"
    assert city.search_places("Фелицына")[0].slug == "felitsyn-museum-krasnodar"

    family = {place.slug for place in city.places_for_category("family")}
    assert {
        "krasnodar-park",
        "safari-park-krasnodar",
        "solnechny-island",
        "kosenko-botanical-garden",
        "chistyakovskaya-grove",
    } <= family

    free = city.places_for_category("free")
    assert len(free) >= 17
    assert all(place.is_free for place in free)


def test_krasnodar_routes_cover_old_city_modern_family_and_museums() -> None:
    city = catalog()
    routes = {route.slug: route for route in city.routes}

    assert {
        "krasnodar-first-walk",
        "krasnodar-old-city",
        "krasnodar-museums",
        "krasnodar-modern",
        "krasnodar-family",
    } <= routes.keys()
    assert "krasnodar-park" in routes["krasnodar-modern"].place_slugs
    assert "safari-park-krasnodar" in routes["krasnodar-family"].place_slugs
    assert "felitsyn-museum-krasnodar" in routes["krasnodar-museums"].place_slugs

from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog

CITY_SLUG = "tyumen"


def catalog():
    return get_catalog(CITY_SLUG)


def test_tyumen_catalog_has_current_local_provenance() -> None:
    city = catalog()
    assert len(city.places) >= 22

    for place in city.places:
        assert 57.10 <= place.latitude <= 57.20
        assert 65.45 <= place.longitude <= 65.62
        assert place.source.checked_at == date(2026, 10, 7)
        source = urlparse(place.source.url)
        assert source.scheme == "https"
        assert source.hostname


def test_tyumen_landmarks_use_specific_sources() -> None:
    city = catalog()
    expected_hosts = {
        "tura-embankment": "visittyumen.ru",
        "lovers-bridge-tyumen": "visittyumen.ru",
        "slovtsov-museum": "www.museum72.ru",
        "city-duma-museum-tyumen": "www.museum72.ru",
        "kolokolnikov-estate": "www.museum72.ru",
        "masharov-house": "www.museum72.ru",
    }

    for slug, expected_host in expected_hosts.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert urlparse(place.source.url).hostname == expected_host


def test_tyumen_search_and_virtual_categories() -> None:
    city = catalog()

    assert city.search_places("мамонт")[0].slug == "city-duma-museum-tyumen"
    assert city.search_places("кошек")[0].slug == "siberian-cats-square"

    family = {place.slug for place in city.places_for_category("family")}
    assert {
        "color-boulevard-tyumen",
        "zatyumensky-ecopark",
        "gilevskaya-grove",
        "slovtsov-museum",
        "future-tech-museum-tyumen",
    } <= family

    free = city.places_for_category("free")
    assert len(free) >= 17
    assert all(place.is_free for place in free)


def test_tyumen_routes_cover_center_museums_family_and_nature() -> None:
    city = catalog()
    routes = {route.slug: route for route in city.routes}

    assert {
        "tyumen-first-walk",
        "tyumen-old-city",
        "tyumen-museums",
        "tyumen-family",
        "tyumen-green",
    } <= routes.keys()
    assert "tura-embankment" in routes["tyumen-first-walk"].place_slugs
    assert "slovtsov-museum" in routes["tyumen-museums"].place_slugs
    assert "zatyumensky-ecopark" in routes["tyumen-green"].place_slugs


def test_tyumen_seed_marks_closed_round_bath_as_exterior_only() -> None:
    place = catalog().place_by_slug("round-bath-tyumen")

    assert place is not None
    assert "закрыто" in place.summary.casefold()
    assert "снаружи" in place.summary.casefold()

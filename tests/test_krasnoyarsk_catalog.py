from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog

CITY_SLUG = "krasnoyarsk"


def catalog():
    return get_catalog(CITY_SLUG)


def test_krasnoyarsk_catalog_has_current_local_provenance() -> None:
    city = catalog()
    assert len(city.places) >= 21

    for place in city.places:
        assert 55.90 <= place.latitude <= 56.06
        assert 92.70 <= place.longitude <= 92.96
        assert place.source.checked_at == date(2026, 10, 6)
        source = urlparse(place.source.url)
        assert source.scheme == "https"
        assert source.hostname


def test_krasnoyarsk_landmarks_use_specific_sources() -> None:
    city = catalog()
    expected_hosts = {
        "paraskeva-chapel-krsk": "www.admkrsk.ru",
        "krasnoyarsk-local-history-museum": "www.kkkm.ru",
        "surikov-art-museum-mira": "surikov-museum.ru",
        "roev-ruchey": "roev.ru",
        "bobrovy-log": "bobrovylog.ru",
        "krasnoyarsk-stolby-east": "kras-stolby.ru",
        "mira-museum-center": "mira1.ru",
    }

    for slug, expected_host in expected_hosts.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert urlparse(place.source.url).hostname == expected_host


def test_krasnoyarsk_search_and_virtual_categories() -> None:
    city = catalog()

    assert city.search_places("Столбы")[0].slug == "krasnoyarsk-stolby-east"
    assert city.search_places("пароход")[0].slug == "saint-nicholas-steamship"

    family = {place.slug for place in city.places_for_category("family")}
    assert {
        "roev-ruchey",
        "bobrovy-log",
        "tatyshev-island",
        "gremyachaya-griva",
        "central-park-krasnoyarsk",
        "mira-museum-center",
    } <= family

    free = city.places_for_category("free")
    assert len(free) >= 13
    assert all(place.is_free for place in free)


def test_krasnoyarsk_routes_cover_city_yenisei_museums_and_nature() -> None:
    city = catalog()
    routes = {route.slug: route for route in city.routes}

    assert {
        "krsk-first-walk",
        "krsk-yenisei",
        "krsk-museums",
        "krsk-family",
        "krsk-hiking",
    } <= routes.keys()
    assert "tatyshev-island" in routes["krsk-yenisei"].place_slugs
    assert "surikov-art-museum-mira" in routes["krsk-museums"].place_slugs
    assert "mira-museum-center" in routes["krsk-museums"].place_slugs
    assert "krasnoyarsk-stolby-east" in routes["krsk-hiking"].place_slugs


def test_krasnoyarsk_seed_handles_temporary_access_changes_fail_safe() -> None:
    city = catalog()
    stolby = city.place_by_slug("krasnoyarsk-stolby-east")

    assert stolby is not None
    assert "режим посещения" in stolby.summary.casefold()
    assert city.place_by_slug("surikov-estate") is None

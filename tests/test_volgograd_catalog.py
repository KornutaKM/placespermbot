from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog

CITY_SLUG = "volgograd"


def catalog():
    return get_catalog(CITY_SLUG)


def test_volgograd_catalog_has_current_local_provenance() -> None:
    city = catalog()
    assert len(city.places) >= 19

    for place in city.places:
        assert 48.45 <= place.latitude <= 48.80
        assert 44.45 <= place.longitude <= 44.65
        assert place.source.checked_at == date(2026, 10, 6)
        source = urlparse(place.source.url)
        assert source.scheme == "https"
        assert source.hostname


def test_volgograd_landmarks_use_specific_sources() -> None:
    city = catalog()
    expected_hosts = {
        "mamaev-kurgan": "stalingrad-battle.ru",
        "stalingrad-battle-panorama": "stalingrad-battle.ru",
        "volgograd-planetarium": "volgogradplanetarium.ru",
        "mashkov-art-museum": "mashkovmuseum.ru",
        "old-sarepta": "sareptamuseum.ru",
        "central-park-vlg": "www.centralparkvlg.ru",
    }

    for slug, expected_host in expected_hosts.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert urlparse(place.source.url).hostname == expected_host


def test_volgograd_search_and_virtual_categories() -> None:
    city = catalog()

    assert city.search_places("родина мать")[0].slug == "motherland-calls"
    assert city.search_places("планетарий")[0].slug == "volgograd-planetarium"

    family = {place.slug for place in city.places_for_category("family")}
    assert {
        "volgograd-planetarium",
        "central-park-vlg",
        "old-sarepta",
        "central-embankment-vlg",
    } <= family

    free = city.places_for_category("free")
    assert len(free) >= 12
    assert all(place.is_free for place in free)


def test_volgograd_routes_cover_center_mamaev_and_south() -> None:
    city = catalog()
    routes = {route.slug: route for route in city.routes}

    assert {
        "vlg-first-walk",
        "vlg-stalingrad-memory",
        "vlg-mamaev-day",
        "vlg-south",
    } <= routes.keys()
    assert "motherland-calls" in routes["vlg-mamaev-day"].place_slugs
    assert "old-sarepta" in routes["vlg-south"].place_slugs

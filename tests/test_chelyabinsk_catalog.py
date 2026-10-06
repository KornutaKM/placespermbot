from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog

CITY_SLUG = "chelyabinsk"


def catalog():
    return get_catalog(CITY_SLUG)


def test_chelyabinsk_catalog_has_current_local_provenance() -> None:
    city = catalog()
    assert len(city.places) >= 22

    for place in city.places:
        assert 55.13 <= place.latitude <= 55.21
        assert 61.27 <= place.longitude <= 61.47
        assert place.source.checked_at == date(2026, 10, 6)
        source = urlparse(place.source.url)
        assert source.scheme == "https"
        assert source.hostname


def test_chelyabinsk_landmarks_use_specific_sources() -> None:
    city = catalog()
    expected_hosts = {
        "south-ural-history-museum": "chelmuseum.ru",
        "chelyabinsk-art-museum": "www.chelmusart.ru",
        "glinka-opera-chelyabinsk": "www.chelopera.ru",
        "chelyabinsk-zoo": "chelzoo.ru",
        "chtz-museum": "www.chtz-uraltrac.ru",
        "grain-museum-chelyabinsk": "muzeyzerna.ru",
    }

    for slug, expected_host in expected_hosts.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert urlparse(place.source.url).hostname == expected_host


def test_chelyabinsk_search_and_virtual_categories() -> None:
    city = catalog()

    assert city.search_places("Кировка")[0].slug == "kirovka-chelyabinsk"
    assert city.search_places("Танкоград")[0].slug in {
        "chtz-museum",
        "tank-volunteers-monument",
    }

    family = {place.slug for place in city.places_for_category("family")}
    assert {
        "chelyabinsk-zoo",
        "gagarin-park-chelyabinsk",
        "children-railway-chelyabinsk",
        "south-ural-history-museum",
        "victory-garden-chelyabinsk",
    } <= family

    free = city.places_for_category("free")
    assert len(free) >= 14
    assert all(place.is_free for place in free)


def test_chelyabinsk_routes_cover_center_family_and_industrial_history() -> None:
    city = catalog()
    routes = {route.slug: route for route in city.routes}

    assert {
        "chel-first-walk",
        "chel-museums",
        "chel-family",
        "chel-tankograd",
        "chel-industrial",
        "chel-unusual",
    } <= routes.keys()
    assert "south-ural-history-museum" in routes["chel-first-walk"].place_slugs
    assert "chelyabinsk-zoo" in routes["chel-family"].place_slugs
    assert "chtz-museum" in routes["chel-tankograd"].place_slugs
    assert "railway-heritage-center-chelyabinsk" in routes["chel-industrial"].place_slugs


def test_chelyabinsk_seed_handles_current_access_limits() -> None:
    city = catalog()
    art = city.place_by_slug("chelyabinsk-art-museum")
    railway = city.place_by_slug("children-railway-chelyabinsk")

    assert art is not None
    assert "действующая площадка" in art.summary.casefold()
    assert railway is not None
    assert "сезон" in railway.summary.casefold()

from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog

CITY_SLUG = "ufa"


def catalog():
    return get_catalog(CITY_SLUG)


def test_ufa_catalog_has_current_local_provenance() -> None:
    city = catalog()
    assert len(city.places) >= 20

    for place in city.places:
        assert 54.70 <= place.latitude <= 54.83
        assert 55.91 <= place.longitude <= 56.06
        assert place.source.checked_at == date(2026, 10, 6)
        source = urlparse(place.source.url)
        assert source.scheme == "https"
        assert source.hostname


def test_ufa_landmarks_use_specific_sources() -> None:
    city = catalog()
    expected_hosts = {
        "national-museum-bashkortostan": "museumrb.ru",
        "nesterov-museum-ufa": "museum-nesterov.ru",
        "ufa-history-museum": "museum-ufa.ru",
        "aksakov-house-ufa": "aksakov-ufa-official.ru",
        "archaeology-ethnography-museum-ufa": "www.ikuzeev.ru",
        "ufa-planetarium": "ufaplanetarium.ru",
        "ufa-botanical-garden": "ufabotgarden.ru",
    }

    for slug, expected_host in expected_hosts.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert urlparse(place.source.url).hostname == expected_host


def test_ufa_search_and_virtual_categories() -> None:
    city = catalog()

    assert city.search_places("Салават")[0].slug == "salavat-yulaev-monument"
    assert city.search_places("планетарий")[0].slug == "ufa-planetarium"

    family = {place.slug for place in city.places_for_category("family")}
    assert {
        "ufa-planetarium",
        "ufa-botanical-garden",
        "yakutov-park-ufa",
        "victory-park-ufa",
        "national-museum-bashkortostan",
    } <= family

    free = city.places_for_category("free")
    assert len(free) >= 12
    assert all(place.is_free for place in free)


def test_ufa_routes_cover_center_belaya_family_and_north() -> None:
    city = catalog()
    routes = {route.slug: route for route in city.routes}

    assert {
        "ufa-first-walk",
        "ufa-belaya",
        "ufa-museums",
        "ufa-family",
        "ufa-north",
    } <= routes.keys()
    assert "salavat-yulaev-monument" in routes["ufa-belaya"].place_slugs
    assert "ufa-planetarium" in routes["ufa-family"].place_slugs
    assert "lyalya-tyulpan" in routes["ufa-north"].place_slugs


def test_salavat_seed_does_not_promise_statue_access_during_restoration() -> None:
    place = catalog().place_by_slug("salavat-yulaev-monument")

    assert place is not None
    assert place.title == "Площадь Салавата Юлаева"
    assert "площад" in place.summary.casefold() or "берег" in place.summary.casefold()

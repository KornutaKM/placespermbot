from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog

CITY_SLUG = "omsk"


def catalog():
    return get_catalog(CITY_SLUG)


def test_omsk_catalog_has_current_local_provenance() -> None:
    city = catalog()
    assert len(city.places) >= 21

    for place in city.places:
        assert 54.93 <= place.latitude <= 55.06
        assert 73.27 <= place.longitude <= 73.43
        assert place.source.checked_at == date(2026, 10, 6)
        source = urlparse(place.source.url)
        assert source.scheme == "https"
        assert source.hostname


def test_omsk_landmarks_use_specific_sources() -> None:
    city = catalog()
    expected_hosts = {
        "omsk-fortress": "omskkrepost.ru",
        "omsk-local-history-museum": "sibmuseum.ru",
        "dostoevsky-museum-omsk": "lit-museum.ru",
        "vrubel-museum": "www.vrubel.ru",
        "liberov-center": "liberov.ru",
        "green-island-omsk": "parkomsk.ru",
    }

    for slug, expected_host in expected_hosts.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert urlparse(place.source.url).hostname == expected_host


def test_omsk_search_and_virtual_categories() -> None:
    city = catalog()

    assert city.search_places("Достоевский")[0].slug == "dostoevsky-museum-omsk"
    assert city.search_places("Степаныч")[0].slug == "stepanych-plumber"

    family = {place.slug for place in city.places_for_category("family")}
    assert {
        "green-island-omsk",
        "bird-harbor-omsk",
        "g-drive-arena",
        "vrubel-museum",
        "vlksm-park-omsk",
    } <= family

    free = city.places_for_category("free")
    assert len(free) >= 16
    assert all(place.is_free for place in free)


def test_omsk_routes_cover_fortress_irtysh_museums_and_family() -> None:
    city = catalog()
    routes = {route.slug: route for route in city.routes}

    assert {
        "omsk-first-walk",
        "omsk-dostoevsky",
        "omsk-museums",
        "omsk-irtysh",
        "omsk-family",
        "omsk-unusual",
    } <= routes.keys()
    assert "omsk-fortress" in routes["omsk-first-walk"].place_slugs
    assert "dostoevsky-museum-omsk" in routes["omsk-dostoevsky"].place_slugs
    assert "green-island-omsk" in routes["omsk-irtysh"].place_slugs
    assert "bird-harbor-omsk" in routes["omsk-family"].place_slugs

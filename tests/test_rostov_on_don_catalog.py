from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog

CITY_SLUG = "rostov-on-don"


def catalog():
    return get_catalog(CITY_SLUG)


def test_rostov_catalog_has_current_local_provenance() -> None:
    city = catalog()
    assert len(city.places) >= 22

    for place in city.places:
        assert 47.18 <= place.latitude <= 47.27
        assert 39.63 <= place.longitude <= 39.78
        assert place.source.checked_at == date(2026, 10, 6)
        source = urlparse(place.source.url)
        assert source.scheme == "https"
        assert source.hostname


def test_rostov_landmarks_use_specific_sources() -> None:
    city = catalog()
    expected_hosts = {
        "rostov-local-history-museum": "www.rostovmuseum.ru",
        "russian-armenian-friendship-museum": "www.rostovmuseum.ru",
        "rostov-fine-arts-museum": "www.romii.ru",
        "rostov-city-history-museum": "museum-rostov.ru",
        "rostov-zoo": "zooparkrostov.ru",
        "sfedu-botanical-garden": "sfedu.ru",
    }

    for slug, expected_host in expected_hosts.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert urlparse(place.source.url).hostname == expected_host


def test_rostov_search_and_virtual_categories() -> None:
    city = catalog()

    assert city.search_places("мозаики")[0].slug == "rostov-underpass-mosaics"
    assert city.search_places("армянской дружбы")[0].slug == "russian-armenian-friendship-museum"

    family = {place.slug for place in city.places_for_category("family")}
    assert {
        "rostov-zoo",
        "sfedu-botanical-garden",
        "levoberezhny-park-rostov",
        "october-revolution-park-rostov",
        "railway-history-museum-rostov",
    } <= family

    free = city.places_for_category("free")
    assert len(free) >= 14
    assert all(place.is_free for place in free)


def test_rostov_routes_cover_don_center_nakhichevan_and_family() -> None:
    city = catalog()
    routes = {route.slug: route for route in city.routes}

    assert {
        "rostov-first-walk",
        "rostov-don",
        "rostov-museums",
        "rostov-nakhichevan",
        "rostov-family",
    } <= routes.keys()
    assert "rostov-arena" in routes["rostov-don"].place_slugs
    assert "rostov-city-history-museum" in routes["rostov-museums"].place_slugs
    assert "surb-khach-rostov" in routes["rostov-nakhichevan"].place_slugs
    assert "rostov-zoo" in routes["rostov-family"].place_slugs


def test_rostov_art_seed_uses_active_chekhova_site() -> None:
    place = catalog().place_by_slug("rostov-fine-arts-museum")

    assert place is not None
    assert "Чехова, 60" in place.title
    assert "действующая площадка" in place.summary.casefold()
    assert catalog().place_by_slug("paramonov-warehouses") is None

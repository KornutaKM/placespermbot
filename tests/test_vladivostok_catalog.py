from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog

CITY_SLUG = "vladivostok"


def catalog():
    return get_catalog(CITY_SLUG)


def test_vladivostok_catalog_has_current_local_provenance() -> None:
    city = catalog()
    assert len(city.places) >= 18

    for place in city.places:
        assert 43.0 <= place.latitude <= 43.25
        assert 131.83 <= place.longitude <= 132.02
        assert place.source.checked_at == date(2026, 10, 6)
        source = urlparse(place.source.url)
        assert source.scheme == "https"
        assert source.hostname


def test_vladivostok_landmarks_use_specific_sources() -> None:
    city = catalog()
    expected_hosts = {
        "golden-bridge-vvo": "visit-primorye.ru",
        "russky-bridge-vvo": "visit-primorye.ru",
        "tokarevsky-lighthouse": "rgo.ru",
        "arseniev-museum-vvo": "arseniev.org",
        "primorsky-oceanarium": "primocean.ru",
        "botanical-garden-vvo": "www.botsad.ru",
    }

    for slug, expected_host in expected_hosts.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert urlparse(place.source.url).hostname == expected_host


def test_vladivostok_search_and_virtual_categories() -> None:
    city = catalog()

    assert city.search_places("маяк")[0].slug == "tokarevsky-lighthouse"
    assert city.search_places("океанариум")[0].slug == "primorsky-oceanarium"

    family = {place.slug for place in city.places_for_category("family")}
    assert {
        "primorsky-oceanarium",
        "botanical-garden-vvo",
        "sportivnaya-harbour",
        "korabelnaya-embankment",
    } <= family

    free = city.places_for_category("free")
    assert len(free) >= 10
    assert all(place.is_free for place in free)


def test_vladivostok_routes_cover_center_sea_and_russky_island() -> None:
    city = catalog()
    routes = {route.slug: route for route in city.routes}

    assert {
        "vvo-first-day",
        "vvo-golden-horn",
        "vvo-russky-island",
        "vvo-museum-day",
    } <= routes.keys()
    assert "primorsky-oceanarium" in routes["vvo-russky-island"].place_slugs
    assert "tokarevsky-lighthouse" in routes["vvo-egersheld"].place_slugs

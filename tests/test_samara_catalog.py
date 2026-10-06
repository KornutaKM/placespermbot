from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog

CITY_SLUG = "samara"


def catalog():
    return get_catalog(CITY_SLUG)


def test_samara_catalog_has_current_local_provenance() -> None:
    city = catalog()
    assert len(city.places) >= 19

    for place in city.places:
        assert 53.18 <= place.latitude <= 53.36
        assert 50.07 <= place.longitude <= 50.22
        assert place.source.checked_at == date(2026, 10, 6)
        source = urlparse(place.source.url)
        assert source.scheme == "https"
        assert source.hostname


def test_samara_landmarks_use_specific_sources() -> None:
    city = catalog()
    expected_hosts = {
        "stalin-bunker-samara": "samara.travel",
        "alabin-museum-samara": "alabin.ru",
        "modern-museum-samara": "samaramodern.ru",
        "samara-art-museum": "artmus.ru",
        "tretyakov-samara": "www.tretyakovgallery.ru",
        "children-art-gallery-samara": "childgal.ru",
        "samara-zoo": "samzoo.ru",
    }

    for slug, expected_host in expected_hosts.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert urlparse(place.source.url).hostname == expected_host


def test_samara_search_and_virtual_categories() -> None:
    city = catalog()

    assert city.search_places("Ладья")[0].slug == "ladya-monument"
    assert city.search_places("модерн")[0].slug in {
        "modern-museum-samara",
        "house-with-elephants-samara",
    }

    family = {place.slug for place in city.places_for_category("family")}
    assert {
        "samara-zoo",
        "tretyakov-samara",
        "children-art-gallery-samara",
        "samara-embankment",
        "helicopter-viewpoint-samara",
    } <= family

    free = city.places_for_category("free")
    assert len(free) >= 12
    assert all(place.is_free for place in free)


def test_samara_routes_cover_history_volga_and_family() -> None:
    city = catalog()
    routes = {route.slug: route for route in city.routes}

    assert {
        "samara-first-walk",
        "samara-volga",
        "samara-museums",
        "samara-family",
        "samara-secret-capital",
    } <= routes.keys()
    assert "stalin-bunker-samara" in routes["samara-secret-capital"].place_slugs
    assert "samara-zoo" in routes["samara-family"].place_slugs
    assert "helicopter-viewpoint-samara" in routes["samara-views"].place_slugs


def test_samara_space_is_not_pinned_to_temporary_location() -> None:
    city = catalog()

    assert all("space" not in place.slug for place in city.places)

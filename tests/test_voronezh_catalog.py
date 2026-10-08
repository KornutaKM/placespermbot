from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog

CITY_SLUG = "voronezh"


def catalog():
    return get_catalog(CITY_SLUG)


def test_voronezh_catalog_has_current_local_provenance() -> None:
    city = catalog()
    assert len(city.places) >= 23

    for place in city.places:
        assert 51.62 <= place.latitude <= 51.72
        assert 39.15 <= place.longitude <= 39.27
        assert place.source.checked_at == date(2026, 10, 6)
        source = urlparse(place.source.url)
        assert source.scheme == "https"
        assert source.hostname


def test_voronezh_landmarks_use_specific_sources() -> None:
    city = catalog()
    expected_hosts = {
        "goto-predestinatsia": "firstship.ru",
        "voronezh-regional-museum": "museum-vrn.ru",
        "arsenal-museum-vrn": "museum-vrn.ru",
        "durov-house-museum-vrn": "museum-vrn.ru",
        "airborne-forces-museum-vrn": "vdvvrn.ru",
        "kramskoy-museum": "mkram.ru",
        "voronezh-zoo": "zooparkvrn.ru",
    }

    for slug, expected_host in expected_hosts.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert urlparse(place.source.url).hostname == expected_host


def test_voronezh_search_and_virtual_categories() -> None:
    city = catalog()

    assert city.search_places("Гото Предестинация")[0].slug == "goto-predestinatsia"
    assert city.search_places("котёнок")[0].slug == "kitten-lizyukov"

    family = {place.slug for place in city.places_for_category("family")}
    assert {
        "voronezh-zoo",
        "scarlet-sails-park-vrn",
        "orlyonok-park-vrn",
        "goto-predestinatsia",
        "white-bim-monument",
    } <= family

    free = city.places_for_category("free")
    assert len(free) >= 16
    assert all(place.is_free for place in free)


def test_voronezh_routes_cover_navy_museums_family_and_memory() -> None:
    city = catalog()
    routes = {route.slug: route for route in city.routes}

    assert {
        "vrn-first-walk",
        "vrn-peter-navy",
        "vrn-museums",
        "vrn-family",
        "vrn-green-center",
        "vrn-war-memory",
        "vrn-unusual",
    } <= routes.keys()
    assert "goto-predestinatsia" in routes["vrn-peter-navy"].place_slugs
    assert "kramskoy-museum" in routes["vrn-museums"].place_slugs
    assert "voronezh-zoo" in routes["vrn-family"].place_slugs
    assert "airborne-forces-museum-vrn" in routes["vrn-war-memory"].place_slugs


def test_voronezh_dedicated_museums_have_plausible_geopoints() -> None:
    city = catalog()
    durov = city.place_by_slug("durov-house-museum-vrn")
    zoo = city.place_by_slug("voronezh-zoo")
    assert durov is not None and zoo is not None
    assert 51.675 <= durov.latitude <= 51.680
    assert 39.220 <= durov.longitude <= 39.230
    assert 51.640 <= zoo.latitude <= 51.645
    assert 39.239 <= zoo.longitude <= 39.246

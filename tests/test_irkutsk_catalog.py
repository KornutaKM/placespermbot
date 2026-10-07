from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog

CITY_SLUG = "irkutsk"


def catalog():
    return get_catalog(CITY_SLUG)


def test_irkutsk_catalog_has_current_local_provenance() -> None:
    city = catalog()
    assert len(city.places) >= 23

    for place in city.places:
        assert 52.23 <= place.latitude <= 52.32
        assert 104.24 <= place.longitude <= 104.36
        assert place.source.checked_at == date(2026, 10, 7)
        source = urlparse(place.source.url)
        assert source.scheme == "https"
        assert source.hostname


def test_irkutsk_landmarks_use_specific_sources() -> None:
    city = catalog()
    expected_hosts = {
        "lower-angara-embankment": "admirk.ru",
        "volkonsky-house": "imd38.ru",
        "trubetskoy-house": "imd38.ru",
        "irkutsk-history-department": "iokm.ru",
        "sukachev-art-museum": "www.museum.irk.ru",
        "irkutsk-city-history-museum": "irkmuseum.ru",
        "irkutsk-planetarium": "www.irkplanetarium.com",
    }

    for slug, expected_host in expected_hosts.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert urlparse(place.source.url).hostname == expected_host


def test_irkutsk_search_and_virtual_categories() -> None:
    city = catalog()

    assert city.search_places("декабристы")[0].slug in {
        "volkonsky-house",
        "trubetskoy-house",
    }
    assert city.search_places("ледокол")[0].slug == "angara-icebreaker"

    family = {place.slug for place in city.places_for_category("family")}
    assert {
        "irkutsk-planetarium",
        "yunost-island-irkutsk",
        "angara-icebreaker",
        "window-to-asia",
        "irkutsk-nature-department",
    } <= family

    free = city.places_for_category("free")
    assert len(free) >= 12
    assert all(place.is_free for place in free)


def test_irkutsk_routes_cover_center_decembrists_museums_and_angara() -> None:
    city = catalog()
    routes = {route.slug: route for route in city.routes}

    assert {
        "irkutsk-first-walk",
        "irkutsk-old-center",
        "irkutsk-decembrists",
        "irkutsk-museums",
        "irkutsk-angara",
    } <= routes.keys()
    assert "lower-angara-embankment" in routes["irkutsk-first-walk"].place_slugs
    assert "volkonsky-house" in routes["irkutsk-decembrists"].place_slugs
    assert "angara-icebreaker" in routes["irkutsk-angara"].place_slugs


def test_irkutsk_seed_marks_children_railway_as_seasonal() -> None:
    place = catalog().place_by_slug("children-railway-irkutsk")

    assert place is not None
    assert "сезон" in place.summary.casefold()
    assert "проверять" in place.summary.casefold()

def test_irkutsk_city_museum_seed_tracks_temporary_closure() -> None:
    city = catalog()
    museum = city.place_by_slug("irkutsk-city-history-museum")
    route = city.route_by_slug("irkutsk-decembrists")

    assert museum is not None
    assert "закрыт" in museum.summary.casefold()
    assert "1 декабря 2026" in museum.summary
    assert route is not None
    assert "irkutsk-city-history-museum" not in route.place_slugs

from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog

CITY_SLUG = "khabarovsk"


def catalog():
    return get_catalog(CITY_SLUG)


def test_khabarovsk_deep_citywide_catalog_with_fresh_sources() -> None:
    city = catalog()
    assert len(city.places) >= 28
    assert len(city.routes) >= 9
    assert len({place.district for place in city.places}) >= 10
    for place in city.places:
        assert 48.43 <= place.latitude <= 48.54
        assert 135.03 <= place.longitude <= 135.13
        assert place.source.checked_at == date(2026, 10, 8)
        parsed = urlparse(place.source.url)
        assert parsed.scheme == "https" and parsed.hostname


def test_khabarovsk_institution_specific_provenance() -> None:
    city = catalog()
    hosts = {
        "grodekov-museum": "hkm.ru",
        "museum-of-amur": "hkm.ru",
        "archaeology-museum-khv": "hkm.ru",
        "far-east-art-museum": "artmuseum27.ru",
        "khabarovsk-city-history-museum": "museumkhv.ru",
        "amur-utes-museum-centre": "habtravel.ru",
        "khabarovsk-circus": "www.culture.ru",
    }
    for slug, host in hosts.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert urlparse(place.source.url).hostname == host


def test_khabarovsk_search_and_virtual_categories() -> None:
    city = catalog()
    assert city.search_places("Гродековского")[0].slug == "child-museum-grodekov" or city.search_places("Гродековского")[0].slug == "archaeology-museum-khv"
    assert city.search_places("Невельского")[0].slug == "nevelskoy-embankment"
    family = {p.slug for p in city.places_for_category("family")}
    assert {
        "child-museum-grodekov", "khabarovsk-circus", "northern-park-khv",
        "city-ponds-khv", "gagarin-park-khv", "grodekov-museum",
    } <= family
    free = city.places_for_category("free")
    assert len(free) >= 18
    assert all(p.is_free for p in free)


def test_khabarovsk_routes_are_unique_and_cover_city_scenarios() -> None:
    city = catalog()
    routes = {r.slug: r for r in city.routes}
    assert {
        "khv-first-walk", "khv-amur-views", "khv-museum-day",
        "khv-old-streets", "khv-family-ponds", "khv-memory",
        "khv-southern-family", "khv-north-green", "khv-station-boulevards",
    } <= routes.keys()
    assert "grodekov-museum" in routes["khv-museum-day"].place_slugs
    assert "nevelskoy-embankment" in routes["khv-amur-views"].place_slugs
    assert "khabarovsk-circus" in routes["khv-southern-family"].place_slugs
    assert "northern-park-khv" in routes["khv-north-green"].place_slugs
    known = {p.slug for p in city.places}
    for route in city.routes:
        assert route.duration_minutes > 0 and route.distance_km > 0
        assert len(set(route.place_slugs)) == len(route.place_slugs)
        assert set(route.place_slugs) <= known


def test_khabarovsk_outer_tourist_sites_and_access_safe_conditions() -> None:
    city = catalog()
    southern = city.place_by_slug("gagarin-park-khv")
    northern = city.place_by_slug("northern-park-khv")
    centre = city.place_by_slug("amur-utes-museum-centre")
    circus = city.place_by_slug("khabarovsk-circus")
    assert southern is not None and northern is not None
    assert centre is not None and circus is not None
    assert southern.latitude < 48.45
    assert northern.latitude > 48.52
    assert "условия посещения" in centre.summary
    assert "проверяются" in circus.summary

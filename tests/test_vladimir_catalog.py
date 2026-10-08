from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog

CITY_SLUG = "vladimir"


def catalog():
    return get_catalog(CITY_SLUG)


def test_vladimir_geo_and_provenance() -> None:
    city = catalog()
    assert len(city.places) >= 30
    assert len(city.routes) >= 9
    assert len({p.district for p in city.places}) >= 10
    for place in city.places:
        assert 56.09 <= place.latitude <= 56.16
        assert 40.32 <= place.longitude <= 40.48
        assert place.source.checked_at == date(2026, 10, 8)
        parsed = urlparse(place.source.url)
        assert parsed.scheme == "https" and parsed.hostname


def test_vladimir_museum_and_landmark_official_sources() -> None:
    city = catalog()
    expected = {
        "vladimir-golden-gates": "vladimirculture.ru",
        "vladimir-assumption-cathedral": "vladimirculture.ru",
        "vladimir-dmitrievsky-cathedral": "vladimirculture.ru",
        "vladimir-historical-museum": "tickets.vladmuseum.ru",
        "vladimir-palaty-museum": "tickets.vladmuseum.ru",
        "vladimir-crystal-museum": "tickets.vladmuseum.ru",
        "old-pharmacy-vladimir": "vc33.ru",
        "spoon-museum-vladimir": "www.culture.ru",
        "vladimir-druzhba-park": "vladimirculture.ru",
    }
    for slug, host in expected.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert urlparse(place.source.url).hostname == host


def test_vladimir_search_and_virtual_categories() -> None:
    city = catalog()
    assert city.search_places("Дмитриевский собор")[0].slug == "vladimir-dmitrievsky-cathedral"
    assert city.search_places("аптека")[0].slug == "old-pharmacy-vladimir"
    family = {p.slug for p in city.places_for_category("family")}
    assert {
        "gingerbread-house-vladimir",
        "babusia-yagusia-vladimir",
        "vladimir-druzhba-park",
        "vladimir-central-park",
        "vladimir-dmitrievsky-cathedral",
    } <= family
    free = city.places_for_category("free")
    assert len(free) >= 16
    assert all(place.is_free for place in free)


def test_vladimir_routes_cover_culture_family_nature_and_crafts() -> None:
    city = catalog()
    routes = {r.slug: r for r in city.routes}
    assert {
        "vl-first-walk", "vl-white-stone", "vl-museum-classics",
        "vl-georgievskaya-crafts", "vl-family-stories", "vl-historic-gardens",
        "vl-fun-unusual", "vl-nature-mira", "vl-dubrovka-family",
    } <= routes.keys()
    assert "vladimir-golden-gates" in routes["vl-first-walk"].place_slugs
    assert "borodin-forge-vladimir" in routes["vl-georgievskaya-crafts"].place_slugs
    assert "babusia-yagusia-vladimir" in routes["vl-family-stories"].place_slugs
    assert "vladimir-central-park" in routes["vl-nature-mira"].place_slugs
    known = {p.slug for p in city.places}
    for route in city.routes:
        assert route.duration_minutes > 0 and route.distance_km > 0
        assert len(route.place_slugs) == len(set(route.place_slugs))
        assert set(route.place_slugs) <= known


def test_vladimir_access_and_city_bounds_regressions() -> None:
    city = catalog()
    gate = city.place_by_slug("vladimir-golden-gates")
    stoletov = city.place_by_slug("stoletov-house-vladimir")
    cathedral = city.place_by_slug("vladimir-assumption-cathedral")
    west = city.place_by_slug("vladimir-druzhba-park")
    east = city.place_by_slug("vladimir-dobroselsky-park")
    assert gate is not None and stoletov is not None
    assert cathedral is not None and west is not None and east is not None
    assert "закрыта на реставрацию" in gate.summary
    assert "не гарантируется" in stoletov.summary
    assert "внешний осмотр" in cathedral.summary
    assert west.longitude < 40.35 and east.longitude > 40.45

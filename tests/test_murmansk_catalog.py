from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog

CITY_SLUG = "murmansk"


def catalog():
    return get_catalog(CITY_SLUG)


def test_murmansk_catalog_depth_provenance_and_bbox() -> None:
    city = catalog()
    assert len(city.places) >= 34
    assert len(city.routes) >= 10
    assert len({p.district for p in city.places}) >= 12
    for place in city.places:
        assert 68.90 <= place.latitude <= 69.10
        assert 33.02 <= place.longitude <= 33.18
        assert place.source.checked_at == date(2026, 10, 8)
        parsed = urlparse(place.source.url)
        assert parsed.scheme == "https" and parsed.hostname


def test_murmansk_institution_provenance() -> None:
    city = catalog()
    hosts = {
        "murmansk-sea-terminal": "www.murmansk.travel",
        "murmansk-icebreaker-lenin": "murmansk.travel",
        "murmansk-regional-museum": "www.murmansk.travel",
        "murmansk-regional-art-museum": "artmmuseum.ru",
        "murmansk-russian-museum-center": "artmmuseum.ru",
        "murmansk-port-history-museum": "murmansk.travel",
        "murmansk-pinro-museum": "www.murmansk.travel",
        "murmansk-alyosha-closed": "www.citymurmansk.ru",
    }
    for slug, host in hosts.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert urlparse(place.source.url).hostname == host


def test_murmansk_search_and_family_free_categories() -> None:
    city = catalog()
    assert city.search_places("Атомный ледокол")[0].slug == "murmansk-icebreaker-lenin"
    assert city.search_places("коту Семёну")[0].slug == "murmansk-cat-semyon"
    family = {p.slug for p in city.places_for_category("family")}
    assert {
        "murmansk-cat-semyon", "murmansk-semenovskoye-attractions",
        "murmansk-icebreaker-lenin", "murmansk-semenovskoye-promenade",
        "murmansk-crafts-house",
    } <= family
    free = city.places_for_category("free")
    assert len(free) >= 19
    assert all(p.is_free for p in free)
    assert "murmansk-alyosha-closed" not in {p.slug for p in free}


def test_murmansk_routes_no_closed_alyosha_and_geographic_scenarios() -> None:
    city = catalog()
    routes = {r.slug: r for r in city.routes}
    assert {
        "mur-first-visit", "mur-maritime", "mur-family-lake",
        "mur-museums", "mur-fishing", "mur-memory-centre",
        "mur-submariners", "mur-crafts-art", "mur-captains",
        "mur-north-waiting", "mur-southern-memory",
    } <= routes.keys()
    assert "murmansk-icebreaker-lenin" in routes["mur-maritime"].place_slugs
    assert "murmansk-pinro-museum" in routes["mur-fishing"].place_slugs
    assert "murmansk-kursk-submariners" in routes["mur-submariners"].place_slugs
    known = {p.slug for p in city.places}
    for route in city.routes:
        assert len(set(route.place_slugs)) == len(route.place_slugs)
        assert set(route.place_slugs) <= known
        assert "murmansk-alyosha-closed" not in route.place_slugs
        assert route.duration_minutes > 0 and route.distance_km > 0


def test_murmansk_alyosha_restricted_and_pinro_appointment() -> None:
    city = catalog()
    alyosha = city.place_by_slug("murmansk-alyosha-closed")
    pinro = city.place_by_slug("murmansk-pinro-museum")
    lake = city.place_by_slug("murmansk-semenovskoye-lake")
    assert alyosha is not None and pinro is not None and lake is not None
    assert "закрыт для посещения" in alyosha.summary
    assert "2028 год" in alyosha.summary
    assert "предварительной записи" in pinro.summary
    assert "Купание опасно" in lake.summary

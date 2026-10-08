from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog


def test_moscow_coverage_and_official_sources() -> None:
    city = get_catalog("moscow")
    assert len(city.places) >= 34
    assert len(city.routes) >= 16
    assert len({p.district for p in city.places}) >= 16
    assert len({p.category for p in city.places}) == 5
    assert sum(p.category == "museums" for p in city.places) >= 11
    for slug, domain in {
        "mos-archeology-museum": "mosmuseum.ru",
        "mos-bulgakov-apartment": "www.bulgakovmuseum.ru",
        "mos-kremlin-armory": "kreml.ru",
        "mos-garden-ring-museum": "mosmuseum.ru",
    }.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert place.source.checked_at == date(2026, 10, 8)
        assert urlparse(place.source.url).hostname == domain


def test_moscow_museum_access_and_remote_routes() -> None:
    city = get_catalog("moscow")
    archeo = city.place_by_slug("mos-archeology-museum")
    armory = city.place_by_slug("mos-kremlin-armory")
    assert archeo is not None and armory is not None
    assert "предварительной записи" in archeo.summary
    assert "Боровицкие ворота" in armory.summary
    assert not archeo.is_free and not armory.is_free
    assert city.search_places("Центр Гиляровского")[0].slug == "mos-gilyarovsky-centre"
    assert "mos-tsaritsyno-ponds" in {p.slug for p in city.places_for_category("free")}
    for slug in ("moscow-parks", "moscow-modern", "moscow-south-estates", "moscow-contemporary-art"):
        route = city.route_by_slug(slug)
        assert route is not None
        assert "транспорт" in route.summary or "метро" in route.summary
    assert all(len(route.place_slugs) >= 2 for route in city.routes)

from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog


def test_kaliningrad_expanded_museum_and_family_catalog() -> None:
    city = get_catalog("kaliningrad")
    assert len(city.places) >= 30
    assert len(city.routes) >= 12
    assert len({p.category for p in city.places}) == 5
    assert len({p.district for p in city.places}) >= 10
    assert sum(p.category == "museums" for p in city.places) >= 10
    for slug, host in {
        "kal-submarine-b413": "www.world-ocean.ru",
        "kal-planet-ocean": "world-ocean.ru",
        "kal-yunost-park": "visit-kaliningrad.ru",
        "kal-brandenburg-gate": "visit-kaliningrad.ru",
    }.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert place.source.checked_at == date(2026, 10, 8)
        assert urlparse(place.source.url).hostname == host


def test_kaliningrad_planet_ocean_access_and_safe_routes() -> None:
    city = get_catalog("kaliningrad")
    planet = city.place_by_slug("kal-planet-ocean")
    depth = city.place_by_slug("kal-depth-building")
    gate = city.place_by_slug("kal-brandenburg-gate")
    assert planet is not None and depth is not None and gate is not None
    assert "отдельным порядком" in planet.summary
    assert "Отдельный" in depth.summary
    assert "с тротуара" in gate.summary
    assert planet.is_free is False and gate.is_free is True
    assert city.search_places("Плавучий маяк")[0].slug == "kal-irbensky-beacon"
    assert "kal-yunost-park" in {p.slug for p in city.places_for_category("family")}
    assert city.route_by_slug("kal-ocean-vessels") is not None
    assert city.route_by_slug("kal-family-north") is not None
    assert all(len(route.place_slugs) >= 2 for route in city.routes)

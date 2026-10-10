from datetime import date

from app.catalog import get_catalog
from app.catalog_quality import validate_catalog_quality
from app.city_manifest import list_city_manifests
from app.route_review import hard_route_findings, inspect_routes


def test_kostroma_city_manifest_and_quality() -> None:
    city = get_catalog("kostroma")
    manifest = next(m for m in list_city_manifests() if m.slug == "kostroma")
    assert len(city.places) == 26
    assert len(city.routes) == 11
    assert len({p.category for p in city.places}) == 5
    assert sum(p.category == "museums" for p in city.places) >= 9
    assert validate_catalog_quality(city, manifest.quality) == ()
    assert hard_route_findings(inspect_routes(city)) == ()


def test_kostroma_routes_are_city_scoped_and_sources_current() -> None:
    city = get_catalog("kostroma")
    assert city.place_by_slug("kst-ipatiev-monastery") is not None
    assert city.place_by_slug("kst-snow-maiden-house").is_free is False
    assert city.search_places("Костромская слобода")[0].slug == "kst-wooden-museum"
    assert all(57.74 <= p.latitude <= 57.80 for p in city.places)
    assert all(40.85 <= p.longitude <= 41.00 for p in city.places)
    assert all(p.source.url.startswith("https://") for p in city.places)
    assert all(p.source.checked_at == date(2026, 10, 10) for p in city.places)
    assert all(p.source.name.strip() for p in city.places)
    assert all(all(city.place_by_slug(slug) for slug in route.place_slugs)
               for route in city.routes)

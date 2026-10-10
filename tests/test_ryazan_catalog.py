from datetime import date

from app.catalog import get_catalog
from app.catalog_quality import validate_catalog_quality
from app.city_manifest import list_city_manifests
from app.route_review import hard_route_findings, inspect_routes


def test_ryazan_is_registered_with_rich_catalog() -> None:
    catalog = get_catalog("ryazan")
    manifest = next(m for m in list_city_manifests() if m.slug == catalog.slug)
    assert len(catalog.places) == 26
    assert len(catalog.routes) == 10
    assert len({place.category for place in catalog.places}) == 5
    assert len({place.district for place in catalog.places}) >= 14
    assert sum(place.category == "museums" for place in catalog.places) >= 9
    assert validate_catalog_quality(catalog, manifest.quality) == ()
    assert hard_route_findings(inspect_routes(catalog)) == ()


def test_ryazan_search_and_local_routes() -> None:
    catalog = get_catalog("ryazan")
    assert catalog.search_places("Павлова")[0].slug == "rya-pavlov-estate"
    assert catalog.search_places("леденца")[0].slug == "rya-lollipop-museum"
    assert catalog.route_by_slug("rya-sweet-city") is not None
    assert catalog.route_by_slug("rya-kremlin-architecture") is not None
    family = {p.slug for p in catalog.places_for_category("family")}
    free = {p.slug for p in catalog.places_for_category("free")}
    assert "rya-gingerbread-gallery" in family
    assert "rya-lollipop-museum" not in free
    assert "rya-kremlin" in free
    assert all(p.source.checked_at == date(2026, 10, 9) for p in catalog.places)
    assert all(p.source.url.startswith("https://") for p in catalog.places)

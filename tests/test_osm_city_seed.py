"""Do not promote fictitious places from the top-100 planning registry."""

import json
from itertools import pairwise
from pathlib import Path

from app.catalog import distance_km, get_catalog
from app.catalog_quality import validate_catalog_quality
from app.catalog_validation import validate_catalog
from app.city_manifest import list_city_manifests
from app.data.osm_seed_2026 import OSM_SEED_CITIES, SNAPSHOT_FILE
from app.route_review import hard_route_findings, inspect_routes
from app.top_city_coverage import RESERVED_SLUGS


def test_all_promoted_seed_catalogs_are_sourced_and_geographically_consistent():
    if not SNAPSHOT_FILE.exists():
        assert OSM_SEED_CITIES == ()
        return
    raw = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
    assert raw["source"] == "OpenStreetMap contributors (ODbL)"
    assert len({city["slug"] for city in raw["cities"]}) == len(raw["cities"])
    expected = {
        c["slug"] for c in raw["cities"] if c.get("places") and not c.get("issues")
    }
    assert expected == {c.slug for c in OSM_SEED_CITIES}
    assert expected.issubset(set(RESERVED_SLUGS.values()))

    manifests = {city.slug: city for city in list_city_manifests()}
    for city in OSM_SEED_CITIES:
        catalog = get_catalog(city.slug)
        entry = next(item for item in raw["cities"] if item["slug"] == city.slug)
        assert catalog.name == entry["name"]
        assert len(catalog.places) >= 12
        assert len(catalog.routes) == 5
        assert not validate_catalog(catalog)
        assert not validate_catalog_quality(catalog, manifests[city.slug].quality)
        assert not hard_route_findings(inspect_routes(catalog))
        assert len({p.slug for p in catalog.places}) == len(catalog.places)
        for place, record in zip(catalog.places, entry["places"], strict=True):
            assert place.slug == record["slug"]
            assert place.source.url == record["source"]["url"]
            assert place.source.name.startswith("© OpenStreetMap")
            assert place.source.url == (
                f"https://www.openstreetmap.org/{record['osm_type']}/{record['osmid']}"
            )
            assert place.latitude == record["latitude"]
            assert place.longitude == record["longitude"]
            assert place.title == record["title"]
            assert place.category == record["category"]
            assert place.source.checked_at.isoformat() == entry["checked_at"]
            assert "not on-site verified" not in place.title
        for route in catalog.routes:
            assert len(route.place_slugs) >= 2
            assert len(route.place_slugs) == len(set(route.place_slugs))
            assert "не проверенный пешеходный маршрут" in route.summary
            points = [catalog.place_by_slug(slug) for slug in route.place_slugs]
            assert all(points)
            assert all(
                distance_km(a, b) <= 3.5
                for a, b in pairwise(points)
            )


def test_osm_data_is_an_explicit_seed_snapshot_with_attribution():
    if SNAPSHOT_FILE.exists():
        raw = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
        assert raw.get("cities")
        assert raw.get("source") == "OpenStreetMap contributors (ODbL)"
    documentation = Path("docs/top100-cities.md").read_text(encoding="utf-8")
    assert "OpenStreetMap" in documentation

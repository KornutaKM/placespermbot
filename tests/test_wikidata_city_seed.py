"""Wikidata is a fallback for map records, never a fabricated editorial catalog."""

import json
from itertools import pairwise

from app.catalog import distance_km, get_catalog
from app.catalog_quality import validate_catalog_quality
from app.catalog_validation import validate_catalog
from app.city_manifest import list_city_manifests
from app.data.osm_seed_2026 import OSM_SEED_CITIES
from app.data.wikidata_seed_2026 import (
    SNAPSHOT_FILE,
    WIKIDATA_REVIEW_ISSUES,
    WIKIDATA_SEED_CITIES,
)
from app.route_review import hard_route_findings, inspect_routes
from app.top_city_coverage import RESERVED_SLUGS, coverage_summary


def test_wikidata_snapshot_never_registers_unsourced_or_duplicate_catalogs():
    if not SNAPSHOT_FILE.is_file():
        assert not WIKIDATA_SEED_CITIES
        return
    snapshot = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
    assert snapshot["source"] == "Wikidata contributors (CC0)"
    assert not WIKIDATA_REVIEW_ISSUES, WIKIDATA_REVIEW_ISSUES
    osm_slugs = {c.slug for c in OSM_SEED_CITIES}
    imported = {c.slug for c in WIKIDATA_SEED_CITIES}
    assert not osm_slugs.intersection(imported)
    assert imported.issubset(set(RESERVED_SLUGS.values()))
    asserted = {
        c["slug"] for c in snapshot["cities"]
        if c.get("places") and not c.get("issues") and c["slug"] not in osm_slugs
    }
    assert asserted == imported
    manifests = {c.slug: c for c in list_city_manifests()}
    assert coverage_summary()["map_seed_count"] == len(OSM_SEED_CITIES) + len(imported)
    for city in WIKIDATA_SEED_CITIES:
        catalog = get_catalog(city.slug)
        record = next(x for x in snapshot["cities"] if x["slug"] == city.slug)
        assert catalog.name == record["name"]
        assert len(catalog.places) >= 12
        assert len(catalog.routes) == 5
        assert not validate_catalog(catalog)
        assert not validate_catalog_quality(catalog, manifests[city.slug].quality)
        assert not hard_route_findings(inspect_routes(catalog))
        assert len({r.place_slugs for r in catalog.routes}) == 5
        assert len({p.slug for p in catalog.places}) == len(catalog.places)
        for place, raw in zip(catalog.places, record["places"], strict=True):
            qid = raw["wikidata_id"]
            assert qid.startswith("Q") and qid[1:].isdigit()
            assert place.source.url == f"https://www.wikidata.org/wiki/{qid}"
            assert place.source.name == "Wikidata contributors (CC0)"
            assert place.title == raw["title"]
            assert place.latitude == raw["latitude"]
            assert place.longitude == raw["longitude"]
            assert place.slug == raw["slug"]
        for route in catalog.routes:
            assert "не проверенный пешеходный маршрут" in route.summary
            pts = [catalog.place_by_slug(slug) for slug in route.place_slugs]
            assert all(pts)
            assert all(distance_km(a, b) <= 5.0 for a, b in pairwise(pts))

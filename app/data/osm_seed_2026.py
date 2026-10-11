"""Snapshot guides from individually linked OpenStreetMap features (ODbL).

Input JSON is acquired in an explicit one-time data review workflow, never
requested from OSM at app runtime. Routes connect nearby map markers *only*
as candidate walks; availability, paths and accessibility are unverified.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from itertools import pairwise
from math import asin, ceil, cos, radians, sin, sqrt
from pathlib import Path

from app.domain import Place, PlaceSource, RoutePlan

CATEGORY_LABELS = {
    "sights": "🏛 Достопримечательности",
    "parks": "🌿 Парки и прогулки",
    "museums": "🖼 Музеи и культура",
    "unusual": "✨ Необычные места",
    "family": "👨‍👩‍👧 С детьми",
}
SNAPSHOT_FILE = Path(__file__).with_name("osm_seed_2026.json")


@dataclass(frozen=True, slots=True)
class OsmSeedCity:
    slug: str
    name: str
    category_labels: dict[str, str]
    places: tuple[Place, ...]
    routes: tuple[RoutePlan, ...]


def _distance_km(a: Place, b: Place) -> float:
    lat1, lat2 = radians(a.latitude), radians(b.latitude)
    dy, dx = lat2 - lat1, radians(b.longitude - a.longitude)
    return 2 * 6371.0088 * asin(sqrt(
        sin(dy / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dx / 2) ** 2
    ))


def _candidate_route(
    slug: str, name: str, key: str, title: str, candidates: tuple[Place, ...],
    *, adjacent: tuple[Place, ...] = (),
    used_signatures: set[tuple[str, ...]] | None = None,
) -> RoutePlan:
    if len(candidates) < 2:
        raise ValueError(f"{slug}/{key}: not enough themed locations")
    # Choose a compact, nontrivial connected pair, not artificial far-apart stops.
    possible = sorted(
        (
            (_distance_km(a, b), a.slug, b.slug, a, b)
            for i, a in enumerate(candidates)
            for b in candidates[i + 1:]
            if 0.08 <= _distance_km(a, b) <= 5.0
        ),
        key=lambda item: (item[0], item[1], item[2]),
    )
    if not possible:
        # Keep a genuine themed stop, but add a real nearby attraction if the
        # few mapped museums/parks are too far apart for a pedestrian route.
        possible = sorted(
            (
                (_distance_km(a, b), a.slug, b.slug, a, b)
                for a in candidates for b in adjacent
                if 0.08 <= _distance_km(a, b) <= 5.0
            ),
            key=lambda item: (item[0], item[1], item[2]),
        )
    if not possible:
        raise ValueError(f"{slug}/{key}: no nearby pair within 5 km")
    for _, _, _, first, second in possible:
        visits = [first, second]
        # A third nearby POI improves the map suggestion without inferring
        # pedestrian networks. Every straight segment stays <= 5 km.
        for place in candidates:
            if place.slug in {p.slug for p in visits}:
                continue
            if 0.08 <= _distance_km(visits[-1], place) <= 1.8:
                visits.append(place)
                break
        signature = tuple(p.slug for p in visits)
        if used_signatures is not None and signature in used_signatures:
            continue
        if used_signatures is not None:
            used_signatures.add(signature)
        straight = sum(_distance_km(a, b) for a, b in pairwise(visits))
        distance = max(0.3, round(straight * 1.5 + 0.3, 1))
        duration = sum(p.visit_minutes for p in visits) + ceil(distance / 4.5 * 60) + 20
        return RoutePlan(
            f"{slug}-osm-{key}",
            f"{name}: {title}",
            "Подборка близких картографических точек по OpenStreetMap. "
            "Это не проверенный пешеходный маршрут: реальные дороги, переходы "
            "и доступность необходимо проверить на карте и на месте.",
            duration, distance, signature,
        )
    raise ValueError(f"{slug}/{key}: no distinct nearby route")


def _compile_city(item: dict) -> OsmSeedCity:
    slug, name = item["slug"], item["name"]
    checked_at = date.fromisoformat(item["checked_at"])
    specs = item["places"]
    if len(specs) < 12 or item.get("issues"):
        raise ValueError(f"{slug}: unresolved evidence gate")
    places = []
    used_slugs = set()
    for raw in specs:
        source = raw["source"]
        if not (
            source["url"].startswith("https://www.openstreetmap.org/")
            and source["name"].startswith("© OpenStreetMap")
            and int(raw["osmid"]) > 0
            and raw["osm_type"] in ("node", "way", "relation")
            and source["url"].endswith(f"/{raw['osm_type']}/{raw['osmid']}")
        ):
            raise ValueError(f"{slug}: invalid OSM provenance")
        if any(ch in raw["title"] + raw["district"] for ch in "<>&"):
            raise ValueError(f"{slug}: unsafe OSM text for Telegram HTML")
        if raw["slug"] in used_slugs:
            raise ValueError(f"{slug}: duplicate imported point")
        used_slugs.add(raw["slug"])
        places.append(Place(
            raw["slug"], raw["title"], raw["category"],
            raw["summary"], raw["emoji"], raw["district"],
            int(raw["visit_minutes"]), bool(raw["is_free"]),
            float(raw["latitude"]), float(raw["longitude"]),
            PlaceSource(source["name"], source["url"], checked_at),
            tuple(raw["tags"]),
        ))
    placed = tuple(places)
    used_routes: set[tuple[str, ...]] = set()
    routes = (
        _candidate_route(
            slug, name, "overview", "Знакомство с местами", placed,
            used_signatures=used_routes,
        ),
        _candidate_route(slug, name, "heritage", "Исторические места",
            tuple(p for p in placed if p.category == "sights"),
            adjacent=tuple(p for p in placed if p.category != "sights"),
            used_signatures=used_routes),
        _candidate_route(slug, name, "culture", "Музеи и культура",
            tuple(p for p in placed if p.category == "museums"),
            adjacent=tuple(p for p in placed if p.category != "museums"),
            used_signatures=used_routes),
        _candidate_route(slug, name, "green", "Зелёные пространства",
            tuple(p for p in placed if p.category == "parks"),
            adjacent=tuple(p for p in placed if p.category != "parks"),
            used_signatures=used_routes),
        _candidate_route(slug, name, "family", "Семейные места",
            tuple(p for p in placed if "с детьми" in p.tags),
            adjacent=tuple(p for p in placed if "с детьми" not in p.tags),
            used_signatures=used_routes),
    )
    return OsmSeedCity(slug, name, CATEGORY_LABELS, placed, routes)


def _load_seed_cities() -> tuple[tuple[OsmSeedCity, ...], tuple[str, ...]]:
    if not SNAPSHOT_FILE.is_file():
        return (), ()
    contents = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
    accepted: list[OsmSeedCity] = []
    rejected: list[str] = []
    for item in contents["cities"]:
        if not item.get("places") or item.get("issues"):
            continue
        try:
            accepted.append(_compile_city(item))
        except (KeyError, ValueError, TypeError) as exc:
            # Invalid OSM entries must not take down the whole bot.
            # CI asserts this review list is empty before merge.
            rejected.append(f"{item.get('slug', '<missing>')}: {exc}")
    return tuple(accepted), tuple(rejected)


OSM_SEED_CITIES, OSM_REVIEW_ISSUES = _load_seed_cities()

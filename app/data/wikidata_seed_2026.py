"""Offline Wikidata candidate guide snapshots (CC0), never live WDQS at runtime.

These are geospatial map records, not independently validated walking routes.
Their unreviewed status is surfaced in the API and Telegram UI.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from app.data.osm_seed_2026 import CATEGORY_LABELS, OSM_SEED_CITIES, _candidate_route
from app.domain import Place, PlaceSource, RoutePlan

SNAPSHOT_FILE = Path(__file__).with_name("wikidata_seed_2026.json")
QID_RE = re.compile(r"Q[1-9][0-9]*")


@dataclass(frozen=True, slots=True)
class WikidataSeedCity:
    slug: str
    name: str
    category_labels: dict[str, str]
    places: tuple[Place, ...]
    routes: tuple[RoutePlan, ...]


def _compile_city(record: dict) -> WikidataSeedCity:
    slug, name = record["slug"], record["name"]
    checked_at = date.fromisoformat(record["checked_at"])
    specs = record["places"]
    if len(specs) < 12 or record.get("issues"):
        raise ValueError(f"{slug}: unresolved Wikidata provenance or quality issues")
    places = []
    seen = set()
    for raw in specs:
        qid = raw["wikidata_id"]
        source = raw["source"]
        if (
            not QID_RE.fullmatch(qid)
            or source["url"] != f"https://www.wikidata.org/wiki/{qid}"
            or source["name"] != "Wikidata contributors (CC0)"
        ):
            raise ValueError(f"{slug}: invalid Wikidata source")
        if raw["slug"] != f"{slug}-wd-{qid.lower()}":
            raise ValueError(f"{slug}: inconsistent Wikidata place slug")
        if raw["slug"] in seen:
            raise ValueError(f"{slug}: duplicate Wikidata record")
        if any(ch in raw["title"] + raw["district"] + raw["summary"] for ch in "<>&"):
            raise ValueError(f"{slug}: unsafe text for Telegram HTML")
        seen.add(raw["slug"])
        places.append(Place(
            raw["slug"], raw["title"], raw["category"], raw["summary"],
            raw["emoji"], raw["district"], int(raw["visit_minutes"]),
            bool(raw["is_free"]), float(raw["latitude"]), float(raw["longitude"]),
            PlaceSource(source["name"], source["url"], checked_at),
            tuple(raw["tags"]),
        ))
    chosen = tuple(places)
    unique: set[tuple[str, ...]] = set()
    routes = (
        _candidate_route(
            slug, name, "overview", "Знакомство с местами", chosen,
            used_signatures=unique,
        ),
        _candidate_route(
            slug, name, "heritage", "Исторические места",
            tuple(p for p in chosen if p.category == "sights"),
            adjacent=tuple(p for p in chosen if p.category != "sights"),
            used_signatures=unique,
        ),
        _candidate_route(
            slug, name, "culture", "Музеи и культура",
            tuple(p for p in chosen if p.category == "museums"),
            adjacent=tuple(p for p in chosen if p.category != "museums"),
            used_signatures=unique,
        ),
        _candidate_route(
            slug, name, "green", "Зелёные пространства",
            tuple(p for p in chosen if p.category == "parks"),
            adjacent=tuple(p for p in chosen if p.category != "parks"),
            used_signatures=unique,
        ),
        _candidate_route(
            slug, name, "family", "Семейные места",
            tuple(p for p in chosen if "с детьми" in p.tags),
            adjacent=tuple(p for p in chosen if "с детьми" not in p.tags),
            used_signatures=unique,
        ),
    )
    return WikidataSeedCity(slug, name, CATEGORY_LABELS, chosen, routes)


def _load() -> tuple[tuple[WikidataSeedCity, ...], tuple[str, ...]]:
    if not SNAPSHOT_FILE.is_file():
        return (), ()
    contents = json.loads(SNAPSHOT_FILE.read_text(encoding="utf-8"))
    if contents.get("source") != "Wikidata contributors (CC0)":
        raise RuntimeError("Unexpected Wikidata snapshot license")
    osm_slugs = {city.slug for city in OSM_SEED_CITIES}
    ready, issues = [], []
    for record in contents["cities"]:
        if not record.get("places") or record.get("issues"):
            continue
        if record["slug"] in osm_slugs:
            continue
        try:
            ready.append(_compile_city(record))
        except (ValueError, KeyError, TypeError) as exc:
            issues.append(f"{record.get('slug', '<missing>')}: {exc}")
    return tuple(ready), tuple(issues)


WIKIDATA_SEED_CITIES, WIKIDATA_REVIEW_ISSUES = _load()

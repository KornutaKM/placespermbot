"""Wikidata fallback for cities whose Overpass extraction failed.

Offline candidate extraction only; WDQS is not called from application code.
Wikidata source data is available under CC0 (https://www.wikidata.org/wiki/Wikidata:Licensing).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from seed_city_guides import distance_km, geocode, valid_city

from app.top_city_coverage import RESERVED_SLUGS, TOP_100_NAMES

SOURCE = Path("app/data/osm_seed_2026.json")
OUT = Path("app/data/wikidata_seed_2026.json")
REPORT = Path("docs/wikidata-seed-research.md")
WDQS = "https://query.wikidata.org/sparql"
USER_AGENT = "PlacesRussiaBot-Research/1.0 (https://github.com/KornutaKM/placespermbot; sourced city guides)"
WKT = re.compile(r"^Point\((-?\d+(?:\.\d+)?) (-?\d+(?:\.\d+)?)\)$")
QID = re.compile(r"^https?://www\.wikidata\.org/entity/(Q[1-9][0-9]*)$")
CATEGORIES = {
    "museums": (
        "музей", "museum", "галере", "gallery", "театр", "theatre", "theater",
        "филармони", "концерт", "concert", "центр культуры", "cultural centre",
    ),
    "parks": (
        "парк", "park", "сквер", "сад", "garden", "бульвар", "boulevard",
        "пляж", "beach", "набережн", "promenade", "зелёная зона",
        "площадь", "square", "памятник природы", "natural monument",
    ),
    "unusual": ("скульптур", "sculpture", "статуя", "statue", "арт-объект",
                "artwork", "смотров", "viewpoint", "обелиск", "obelisk"),
    "family": ("зоопарк", "zoo", "океанариум", "aquarium",
               "парк развлеч", "amusement park", "theme park"),
    "sights": (
        "памятник", "монумент", "monument", "memorial", "церковь", "church",
        "собор", "cathedral", "храм", "temple", "крепость", "fortress",
        "замок", "castle", "усадьб", "manor", "дворец", "palace",
        "мечеть", "mosque", "мост", "bridge",
        "памятник архитектуры", "памятник истории", "культурная ценность",
        "культурного наследия", "cultural heritage", "architectur",
    ),
}
EMOJI = {"sights": "🏛", "museums": "🖼", "parks": "🌿",
         "unusual": "✨", "family": "👨‍👩‍👧"}


def category(type_name: str) -> str | None:
    text = type_name.casefold().replace("ё", "е")
    # Public outdoor squares and nature sites belong to the walking category;
    # historic buildings are not automatically museums.
    if "памятник природы" in text or "natural monument" in text:
        return "parks"
    if any(term in text for term in (
        "памятник архитектуры", "памятник истории", "культурная ценность",
        "культурного наследия", "cultural heritage",
    )):
        return "sights"
    if text in {"памятник", "монумент", "monument", "memorial"}:
        return "unusual"
    for name, markers in CATEGORIES.items():
        if any(marker in text for marker in markers):
            return name
    return None


def wiki_results(lat: float, lon: float) -> list[dict]:
    query = f"""SELECT DISTINCT ?item ?itemLabel ?typeLabel ?coordinates WHERE {{
      SERVICE wikibase:around {{
        ?item wdt:P625 ?coordinates .
        bd:serviceParam wikibase:center "Point({lon:.6f} {lat:.6f})"^^geo:wktLiteral .
        bd:serviceParam wikibase:radius "9" .
      }}
      ?item wdt:P31 ?type .
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "ru,en". }}
    }} LIMIT 1200"""
    headers = {"User-Agent": USER_AGENT,
               "Accept": "application/sparql-results+json"}
    url = WDQS + "?" + urlencode({"query": query, "format": "json"})
    response = {}
    for attempt in range(2):
        try:
            with urlopen(Request(url, headers=headers), timeout=90) as raw:
                payload = raw.read(6_000_000)
            response = json.loads(payload)
            break
        except (HTTPError, URLError, TimeoutError, ValueError) as exc:
            if attempt == 1:
                raise RuntimeError(f"Wikidata query unavailable: {exc}") from exc
            time.sleep(8)
    time.sleep(2)
    return response["results"]["bindings"]


def compass(lat: float, lon: float, center_lat: float, center_lon: float) -> str:
    dy = (lat - center_lat) * 111
    dx = (lon - center_lon) * 111 * math.cos(math.radians(center_lat))
    if math.hypot(dx, dy) < 0.9:
        return "Близ центра"
    vertical = "Север" if dy >= 0 else "Юг"
    horizontal = "Восток" if dx >= 0 else "Запад"
    if abs(dy) > 1.6 * abs(dx):
        return vertical
    if abs(dx) > 1.6 * abs(dy):
        return horizontal
    return vertical + "о-" + horizontal.lower()


def to_place(row: dict, *, name: str, slug: str, lat: float, lon: float) -> dict | None:
    try:
        q_url = row["item"]["value"]
        q = QID.fullmatch(q_url)
        label = row["itemLabel"]["value"].strip()
        class_name = row["typeLabel"]["value"].strip()
        match = WKT.fullmatch(row["coordinates"]["value"])
    except (KeyError, TypeError):
        return None
    if not q or not match or label.startswith("Q") and label[1:].isdigit():
        return None
    if not 5 <= len(label) <= 105 or any(ch in label for ch in "<>&\n\r"):
        return None
    cat = category(class_name)
    if cat is None:
        return None
    p_lon, p_lat = float(match[1]), float(match[2])
    if distance_km(lat, lon, p_lat, p_lon) > 9.2:
        return None
    description = (
        f"Картографическая запись Wikidata: тип «{class_name}». "
        "Время посещения, доступность и цены не проверены; "
        "уточните информацию перед поездкой."
    )
    if any(ch in description for ch in "<>&"):
        return None
    outdoor = cat in ("sights", "parks", "unusual")
    family = cat in ("sights", "parks", "museums", "family")
    tags = [cat, "картография", "Wikidata"]
    if family:
        tags.append("с детьми")
    if outdoor:
        tags.append("бесплатно")
    return {
        "slug": f"{slug}-wd-{q[1].lower()}",
        "title": label,
        "category": cat,
        "summary": description,
        "emoji": EMOJI[cat],
        "district": compass(p_lat, p_lon, lat, lon),
        "visit_minutes": 60 if cat == "museums" else 50,
        "is_free": outdoor,
        "latitude": round(p_lat, 6),
        "longitude": round(p_lon, 6),
        "tags": tags,
        "source": {"name": "Wikidata contributors (CC0)",
                   "url": f"https://www.wikidata.org/wiki/{q[1]}"},
        "wikidata_id": q[1],
        "rank_score": (
            (50 if cat == "museums" else 35 if cat == "parks" else 20)
            + max(0, 30 - distance_km(lat, lon, p_lat, p_lon))
        ),
    }


def pick_places(items: list[dict]) -> tuple[list[dict], dict]:
    possible = sorted(items, key=lambda p: (-p["rank_score"], p["slug"]))
    by_title: dict[str, dict] = {}
    for p in possible:
        by_title.setdefault(p["title"].casefold().replace("ё", "е"), p)
    possible = list(by_title.values())
    groups = {cat: [p for p in possible if p["category"] == cat] for cat in CATEGORIES}
    chosen, seen = [], set()
    for cat, minimum in (
        ("museums", 2), ("parks", 3), ("sights", 3), ("unusual", 1), ("family", 1)
    ):
        for p in groups[cat][:minimum]:
            if p["slug"] not in seen:
                chosen.append(p)
                seen.add(p["slug"])
    districts = {p["district"] for p in chosen}
    for p in possible:
        if len(chosen) >= 18 or len(districts) >= 5:
            break
        if p["slug"] not in seen and p["district"] not in districts:
            chosen.append(p)
            seen.add(p["slug"])
            districts.add(p["district"])
    for p in possible:
        if len(chosen) >= 18:
            break
        if p["slug"] not in seen:
            chosen.append(p)
            seen.add(p["slug"])
    chosen.sort(key=lambda p: (-p["rank_score"], p["slug"]))
    return chosen, {
        "available": {cat: len(groups[cat]) for cat in CATEGORIES},
        "selected": {cat: sum(p["category"] == cat for p in chosen) for cat in CATEGORIES},
        "districts": len({p["district"] for p in chosen}),
        "families": sum("с детьми" in p["tags"] for p in chosen),
        "free": sum(p["is_free"] for p in chosen),
    }


def seed_city(name: str, slug: str) -> dict:
    lat, lon, geocoded_name = geocode(name)
    print(f"  Geocoded {name}: {lat}, {lon} ({geocoded_name})", flush=True)
    result = wiki_results(lat, lon)
    items = []
    for row in result:
        entry = to_place(row, name=name, slug=slug, lat=lat, lon=lon)
        if entry:
            items.append(entry)
    places, stats = pick_places(items)
    issues = valid_city(places, stats)
    return {
        "slug": slug, "name": name, "center": [lat, lon],
        "checked_at": datetime.now(UTC).date().isoformat(),
        "places": places if not issues else [],
        "review_candidates": places if issues else [],
        "issues": issues,
        "stats": stats,
        "observed_wikidata_bindings": len(result),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=59)
    parser.add_argument("--refresh", action="store_true",
                        help="Reclassify existing Wikidata seeds after taxonomy updates")
    args = parser.parse_args()
    if not 1 <= args.limit <= 59:
        parser.error("--limit must be 1..59")
    osm = json.loads(SOURCE.read_text(encoding="utf-8"))
    ready = {city["slug"] for city in osm["cities"] if city.get("places")}
    previous = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"cities": []}
    existing = {city["slug"]: city for city in previous["cities"] if city.get("places")}
    targets = [(name, RESERVED_SLUGS[name]) for name in TOP_100_NAMES
               if name in RESERVED_SLUGS and RESERVED_SLUGS[name] not in ready]
    results = []
    for i, (name, slug) in enumerate(targets[:args.limit], 1):
        print(f"[Wikidata {i}/{min(args.limit, len(targets))}] {name}", flush=True)
        if slug in existing and not args.refresh:
            item = existing[slug]
        else:
            try:
                item = seed_city(name, slug)
            except (OSError, RuntimeError, ValueError, KeyError) as exc:
                print(f"  ERROR {type(exc).__name__}: {exc}", flush=True)
                item = {"name": name, "slug": slug, "places": [],
                        "issues": [str(exc)[:200]], "stats": {}}
        results.append(item)
        OUT.write_text(json.dumps({
            "source": "Wikidata contributors (CC0)",
            "cities": results + [c for c in previous["cities"]
                                 if c["slug"] not in {r["slug"] for r in results}],
        }, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    REPORT.write_text(
        "# Wikidata fallback research (CC0)\n\n"
        "Candidates are not editorially reviewed, field verified or guaranteed accessible.\n\n"
        + "\n".join(f"- {r['name']}: {'READY' if r['places'] else 'REVIEW'}; "
                    f"{len(r['places'])} POI; {', '.join(r.get('issues') or ['none'])}"
                    for r in results) + "\n",
        encoding="utf-8",
    )
    print(f"Wikidata: ready={sum(bool(r['places']) for r in results)}/{len(results)}",
          flush=True)


if __name__ == "__main__":
    main()

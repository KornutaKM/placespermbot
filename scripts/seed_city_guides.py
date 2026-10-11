"""One-time, reviewable OSM seed extractor. Never runs in production.

Usage: python scripts/seed_city_guides.py --limit 59
Data: © OpenStreetMap contributors (ODbL 1.0).
The map contains candidate points, NOT independently field-verified itineraries.
"""
from __future__ import annotations

import argparse
import json
import math
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.top_city_coverage import RESERVED_SLUGS, TOP_100_NAMES

OUT = Path("app/data/osm_seed_2026.json")
REPORT = Path("docs/osm-seed-research.md")
USER_AGENT = "PlacesRussiaBot/1.0 (https://github.com/KornutaKM/placespermbot; research snapshot)"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
OVERPASS = (
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
)
RADIUS = 9000
MIN_REQUEST_GAP_SECONDS = 2.0

LABELS = {
    "sights": "Достопримечательности",
    "museums": "Музеи и культура",
    "parks": "Парки и прогулки",
    "unusual": "Необычные места",
    "family": "С детьми",
}
SKIP_NAMES = {"парк", "сквер", "музей", "памятник", "площадь", "библиотека"}
EMOJI = {"sights": "🏛", "museums": "🖼", "parks": "🌿",
         "unusual": "✨", "family": "👨‍👩‍👧"}

def fetch_json(url: str, *, params: dict | None = None, post: str | None = None) -> dict | list:
    target = url + ("?" + urlencode(params) if params else "")
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json",
               "Accept-Language": "ru"}
    data = urlencode({"data": post}).encode() if post is not None else None
    if data is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = Request(target, headers=headers, data=data)
    with urlopen(request, timeout=90) as response:
        body = response.read(8_000_000)
    if len(body) >= 8_000_000:
        raise ValueError("Query response too large")
    return json.loads(body)

def geocode(name: str) -> tuple[float, float, str]:
    # Single-purpose, serial requests with a real project UA; do not bulk crawl.
    for query in (f"{name}, Россия", f"{name}, Russia"):
        result = fetch_json(NOMINATIM, params={
            "q": query, "format": "jsonv2", "limit": 6,
            "addressdetails": 1, "accept-language": "ru",
        })
        time.sleep(MIN_REQUEST_GAP_SECONDS)
        for item in result:
            if item.get("address", {}).get("country_code") != "ru":
                continue
            typ = item.get("type", "")
            if typ not in {"city", "town", "administrative", "municipality"}:
                continue
            return float(item["lat"]), float(item["lon"]), item.get("display_name", "")
    raise ValueError(f"Cannot locate {name} in Russia")

def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    a, b = math.radians(lat1), math.radians(lat2)
    dy, dx = b - a, math.radians(lon2 - lon1)
    return 12742.0176 * math.asin(math.sqrt(
        math.sin(dy / 2) ** 2 + math.cos(a) * math.cos(b) * math.sin(dx / 2) ** 2
    ))

def osm_query(lat: float, lon: float) -> dict:
    around = f"(around:{RADIUS},{lat:.6f},{lon:.6f})"
    lines = [
        f'nwr{around}["name"]["tourism"~"^(museum|gallery|attraction|artwork|viewpoint|zoo|theme_park|aquarium)$"];',
        f'nwr{around}["name"]["historic"~"^(monument|memorial|castle|fort|ruins|archaeological_site|manor)$"];',
        f'nwr{around}["name"]["leisure"~"^(park|garden|nature_reserve)$"];',
        f'nwr{around}["name"]["amenity"~"^(theatre|arts_centre|planetarium)$"];',
    ]
    query = "[out:json][timeout:70];(" + "".join(lines) + ");out center tags;"
    errors = []
    for endpoint in OVERPASS:
        try:
            data = fetch_json(endpoint, post=query)
            if not isinstance(data, dict) or "elements" not in data:
                raise ValueError("No Overpass elements in response")
            time.sleep(MIN_REQUEST_GAP_SECONDS)
            return data
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{endpoint}: {str(exc)[:100]}")
            # Public Overpass instances ask for at least 30s after rate limiting.
            if isinstance(exc, HTTPError) and exc.code in (406, 429):
                time.sleep(30)
            else:
                time.sleep(2)
    raise RuntimeError("OSM query failed: " + "; ".join(errors))

def category_for(tags: dict) -> str | None:
    tourism = tags.get("tourism")
    historic = tags.get("historic")
    leisure = tags.get("leisure")
    amenity = tags.get("amenity")
    if tourism in ("museum", "gallery") or amenity in (
        "theatre", "arts_centre", "planetarium"
    ):
        return "museums"
    if tourism in ("zoo", "aquarium", "theme_park"):
        return "family"
    if leisure in ("park", "garden", "nature_reserve"):
        return "parks"
    if tourism in ("artwork", "viewpoint"):
        return "unusual"
    if tourism == "attraction" or historic in (
        "monument", "memorial", "castle", "fort", "ruins", "archaeological_site", "manor"
    ):
        return "sights"
    return None

def as_place(item: dict, lat: float, lon: float, city_slug: str) -> dict | None:
    tags = item.get("tags") or {}
    title = (tags.get("name:ru") or tags.get("name") or "").strip()
    if not (5 <= len(title) <= 110) or title.casefold() in SKIP_NAMES:
        return None
    if any(ch in title for ch in "<>\\\n\r"):
        return None
    if tags.get("access") in ("private", "no") or tags.get("disused") == "yes":
        return None
    cat = category_for(tags)
    if not cat or item.get("type") not in ("node", "way", "relation"):
        return None
    coord = item if "lat" in item else item.get("center", {})
    try:
        p_lat, p_lon = float(coord["lat"]), float(coord["lon"])
    except (KeyError, TypeError, ValueError):
        return None
    if not (distance_km(lat, lon, p_lat, p_lon) <= 9.2):
        return None
    element_type, osmid = item["type"], int(item["id"])
    unique_id = f"{element_type}-{osmid}"
    street = tags.get("addr:street", "")
    suburb = tags.get("addr:suburb") or tags.get("addr:district")
    if isinstance(suburb, str) and 3 <= len(suburb) <= 70:
        district = suburb
    elif isinstance(street, str) and 4 <= len(street) <= 60:
        district = street
    else:
        d_lat, d_lon = p_lat - lat, (p_lon - lon) * math.cos(math.radians(lat))
        if abs(d_lat) + abs(d_lon) < 0.008:
            district = "Близ центра"
        elif abs(d_lat) > abs(d_lon):
            district = "Севернее центра" if d_lat > 0 else "Южнее центра"
        else:
            district = "Восточнее центра" if d_lon > 0 else "Западнее центра"
    if cat == "museums":
        subject = "Культурный объект"
    elif cat == "parks":
        subject = "Зелёная зона"
    elif cat == "unusual":
        subject = "Арт-объект или видовая точка"
    elif cat == "family":
        subject = "Объект досуга"
    else:
        subject = "Исторический объект или достопримечательность"
    desc = (
        f"{subject}, обозначенный на OpenStreetMap. Координаты и доступность "
        "требуют проверки на месте; часы работы и цены не подтверждены."
    )
    outdoor = cat in ("parks", "sights", "unusual")
    free = outdoor and tags.get("fee") != "yes" and tags.get("access") != "customers"
    family = cat in ("family", "parks", "museums", "sights")
    place_tags = [cat, "город", "картография"]
    if family:
        place_tags.append("с детьми")
    if free:
        place_tags.append("бесплатно")
    return {
        "slug": f"{city_slug}-osm-{unique_id}",
        "title": title,
        "category": cat,
        "summary": desc,
        "emoji": EMOJI[cat],
        "district": district,
        "visit_minutes": 60 if cat == "museums" else (75 if cat == "parks" else 40),
        "is_free": free,
        "latitude": round(p_lat, 6),
        "longitude": round(p_lon, 6),
        "tags": place_tags,
        "source": {
            "name": "© OpenStreetMap contributors (ODbL)",
            "url": f"https://www.openstreetmap.org/{element_type}/{osmid}",
        },
        "osm_tags": {
            k: tags[k] for k in (
                "tourism", "historic", "leisure", "amenity", "wikidata",
                "wikipedia", "website", "heritage", "addr:street",
                "name", "name:ru",
            ) if k in tags
        },
        "osmid": osmid,
        "osm_type": element_type,
        "rank_score": (
            100 if tags.get("wikipedia") or tags.get("wikidata") else 0
        ) + (
            15 if cat == "museums" else 0
        ) + (
            10 if cat == "sights" else 0
        ) + max(0, 20 - distance_km(lat, lon, p_lat, p_lon)),
    }

def choose_places(data: dict, lat: float, lon: float, slug: str) -> tuple[list, dict]:
    possible = [p for item in data["elements"] if (
        p := as_place(item, lat, lon, slug)
    )]
    possible.sort(key=lambda p: (-p["rank_score"], p["slug"]))
    distinct = {}
    for place in possible:
        distinct.setdefault(place["title"].casefold().replace("ё", "е"), place)
    all_items = list(distinct.values())
    group = {category: [p for p in all_items if p["category"] == category]
             for category in LABELS}
    selection = []
    taken = set()
    for category, minimum in (
        ("museums", 2), ("parks", 3), ("sights", 3),
        ("unusual", 1), ("family", 1),
    ):
        for place in group[category][:minimum]:
            if place["slug"] not in taken:
                selection.append(place)
                taken.add(place["slug"])
    for place in all_items:
        if len(selection) >= 18:
            break
        if place["slug"] not in taken:
            selection.append(place)
            taken.add(place["slug"])
    selection.sort(key=lambda p: (-p["rank_score"], p["slug"]))
    meta = {
        "available": {cat: len(group[cat]) for cat in LABELS},
        "selected": {cat: sum(p["category"] == cat for p in selection) for cat in LABELS},
        "districts": len({p["district"] for p in selection}),
        "families": sum("с детьми" in p["tags"] for p in selection),
        "free": sum(p["is_free"] for p in selection),
    }
    return selection, meta

def valid_city(places: list, meta: dict) -> list[str]:
    issues = []
    checks = {
        "places": (len(places), 12),
        "districts": (meta["districts"], 5),
        "categories": (sum(n > 0 for n in meta["selected"].values()), 4),
        "free": (meta["free"], 5),
        "family": (meta["families"], 6),
        "museums": (meta["selected"]["museums"], 2),
        "parks": (meta["selected"]["parks"], 2),
        "sights": (meta["selected"]["sights"], 2),
    }
    for key, (actual, minimum) in checks.items():
        if actual < minimum:
            issues.append(f"{key}: {actual} < {minimum}")
    return issues

def seed_one(name: str, slug: str) -> dict:
    lat, lon, geocode_label = geocode(name)
    print(f"  Geocoded {name}: {lat},{lon} ({geocode_label})", flush=True)
    raw = osm_query(lat, lon)
    places, meta = choose_places(raw, lat, lon, slug)
    issues = valid_city(places, meta)
    return {
        "slug": slug,
        "name": name,
        "center": [lat, lon],
        "checked_at": datetime.now(UTC).date().isoformat(),
        "places": places if not issues else [],
        "issues": issues,
        "stats": meta,
        "observed_objects": len(raw["elements"]),
        "osm_base_timestamp": raw.get("osm3s", {}).get("timestamp_osm_base"),
    }

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=59)
    args = parser.parse_args()
    if not 1 <= args.limit <= 59:
        parser.error("--limit must be 1..59")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    previous = json.loads(OUT.read_text()) if OUT.exists() else {"cities": []}
    completed = {c["slug"]: c for c in previous["cities"] if c.get("places")}
    lines = ["# OSM candidate city guide acquisition", "", ("⚠️ Extracted OSM map data; not on-site verified. "
             "Routes are geometric suggestions and must be checked before field publication."),
             "", "© OpenStreetMap contributors, ODbL 1.0. See https://www.openstreetmap.org/copyright",
             ""]
    selected = [(name, RESERVED_SLUGS[name]) for name in TOP_100_NAMES
                if name in RESERVED_SLUGS][:args.limit]
    results = []
    for i, (name, slug) in enumerate(selected, 1):
        print(f"[{i}/{len(selected)}] {name}", flush=True)
        if slug in completed:
            result = completed[slug]
        else:
            try:
                result = seed_one(name, slug)
            except (OSError, ValueError, RuntimeError, KeyError) as exc:
                print(f"  ERROR {type(exc).__name__}: {exc}", flush=True)
                result = {"slug": slug, "name": name, "places": [],
                          "issues": [str(exc)[:200]], "stats": {}}
        results.append(result)
        status = "READY" if result["places"] else "REVIEW"
        lines.append(f"- **{name}** ({slug}): {status}; "
                     f"{len(result['places'])} POI; issues: "
                     f"{', '.join(result.get('issues') or ['none'])}")
        # Persist every city's real map evidence so interrupted runs can resume.
        OUT.write_text(json.dumps({"source": "OpenStreetMap contributors (ODbL)",
            "cities": results + [c for c in previous["cities"]
                                 if c["slug"] not in {item["slug"] for item in results}]},
            ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ready = sum(bool(c["places"]) for c in results)
    print(f"OSM snapshot: ready={ready}/{len(selected)}, review={len(selected)-ready}", flush=True)

if __name__ == "__main__":
    main()

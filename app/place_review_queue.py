"""Turn all-city source probes into a usable, evidence-safe editorial queue.

No automatic publication, deletion, certification or user-data mutation.
An absent OSM object, HTTP error or changed tag is a *review signal* only.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

from app.catalog import CityCatalog, list_catalogs
from app.withheld_places import WITHHELD_PLACES

CRITICAL_SIGNALS = frozenset({
    "mapped_inactive_review_required",
    "mapped_access_restriction_review_required",
    "wikidata_end_date_review_required",
})
MISSING_SIGNALS = frozenset({
    "source_missing_review_required",
    "map_feature_missing_review_required",
    "wikidata_item_missing_review_required",
})
RETRY_SIGNALS = frozenset({
    "probe_blocked_or_throttled",
    "probe_inconclusive",
})
PASSIVE_SIGNALS = frozenset({
    "map_feature_present_not_venue_verified",
    "wikidata_item_present_not_venue_verified",
    "source_reachable_not_venue_verified",
    "not_probed",
})
ALLOWED_SIGNALS = (
    CRITICAL_SIGNALS | MISSING_SIGNALS | RETRY_SIGNALS | PASSIVE_SIGNALS
)


def priority_for_signal(signal: str) -> str | None:
    if signal in CRITICAL_SIGNALS:
        return "P0_documentary_investigation"
    if signal in MISSING_SIGNALS:
        return "P1_source_identity_review"
    if signal in RETRY_SIGNALS:
        return "P2_retry_or_manual_source"
    return None


def _clean_cell(value: object) -> str:
    """Keep untrusted map titles/URLs from breaking workflow Markdown tables."""
    return (
        str(value).replace("|", "\\|").replace("\n", " ")
        .replace("\r", " ").replace("<", "&lt;").replace(">", "&gt;")
    )


def build_review_queue(
    scan: dict, *, catalogs: tuple[CityCatalog, ...] | None = None,
    previous: dict | None = None,
) -> dict:
    active = list_catalogs() if catalogs is None else catalogs
    by_id = {
        (catalog.slug, place.slug): (catalog, place)
        for catalog in active for place in catalog.places
    }
    rows = scan.get("places", [])
    if not isinstance(rows, list):
        raise ValueError("Scan must contain a list of places")
    received = [(row.get("city_slug"), row.get("place_slug")) for row in rows]
    if (
        len(received) != len(by_id)
        or len(set(received)) != len(received)
        or set(received) != set(by_id)
        or scan.get("place_count") != len(by_id)
        or scan.get("city_count") != len(active)
    ):
        raise ValueError("Source scan must cover every active place exactly once")
    old_signals = {}
    if previous is not None:
        old_signals = {
            (row["city_slug"], row["place_slug"]): row.get("probe", {}).get("signal")
            for row in previous.get("places", [])
        }
    route_impact = defaultdict(list)
    for catalog in active:
        for route in catalog.routes:
            for slug in route.place_slugs:
                route_impact[(catalog.slug, slug)].append(route.slug)

    queue = []
    by_city = {
        catalog.slug: {
            "slug": catalog.slug,
            "name": catalog.name,
            "total": len(catalog.places),
            "critical": 0,
            "source_missing": 0,
            "retry": 0,
            "operator_listings": 0,
            "not_documented_by_operator": 0,
            "route_stops_impacted": 0,
            "withheld": 0,
        }
        for catalog in active
    }
    for row in rows:
        key = (row["city_slug"], row["place_slug"])
        catalog, place = by_id[key]
        if row.get("source_url") != place.source.url:
            raise ValueError(f"{key}: source URL in scan differs from the catalog")
        signal = row.get("probe", {}).get("signal")
        if signal not in ALLOWED_SIGNALS:
            raise ValueError(f"{key}: unknown probe signal: {signal}")
        evidence = row.get("published_evidence") or {}
        if evidence.get("status") == "operator_listed":
            by_city[catalog.slug]["operator_listings"] += 1
        else:
            by_city[catalog.slug]["not_documented_by_operator"] += 1
        priority = priority_for_signal(signal)
        if priority is None:
            continue
        metric = (
            "critical" if signal in CRITICAL_SIGNALS else
            "source_missing" if signal in MISSING_SIGNALS else "retry"
        )
        by_city[catalog.slug][metric] += 1
        routes = sorted(set(route_impact[key]))
        by_city[catalog.slug]["route_stops_impacted"] += len(routes)
        queue.append({
            "city_slug": catalog.slug,
            "city_name": catalog.name,
            "place_slug": place.slug,
            "title": place.title,
            "priority": priority,
            "signal": signal,
            "source_url": place.source.url,
            "route_slugs": routes,
            "route_count": len(routes),
            "probe_details": row["probe"],
            "operator_evidence": evidence,
            "previous_signal": old_signals.get(key),
            "new_or_changed": (
                previous is not None and old_signals.get(key) != signal
            ),
            "disposition": (
                "independent evidence needed; do not delete automatically"
                if signal in CRITICAL_SIGNALS | MISSING_SIGNALS else
                "retry URL and find alternate source; do not interpret as closure"
            ),
        })
    tracked_withheld = scan.get("withheld_review_watch", [])
    expected_withheld = {(p.city_slug, p.place_slug) for p in WITHHELD_PLACES}
    got_withheld = {
        (record["city_slug"], record["place_slug"]) for record in tracked_withheld
    }
    if got_withheld != expected_withheld or len(tracked_withheld) != len(expected_withheld):
        raise ValueError("Scan has missing or duplicated withheld-place watches")
    withheld_rows = []
    for record in tracked_withheld:
        by_city[record["city_slug"]]["withheld"] += 1
        withheld_rows.append({
            **record,
            "priority": "P0_withheld_until_operator_opening",
            "disposition": (
                "keep excluded until dated operator or municipality confirmation; "
                "OSM tag change alone does not authorize reinstatement"
            ),
        })
    queue.sort(key=lambda q: (q["priority"], -q["route_count"], q["city_name"], q["title"]))
    counts = Counter(entry["priority"] for entry in queue)
    return {
        "produced_at": datetime.now(UTC).isoformat(),
        "scan_date": scan.get("date"),
        "scope": "all-city source drift triage; not independent proof of visiting access",
        "live_probe": scan.get("probe_mode") == "live",
        "city_count": len(active),
        "active_place_count": len(by_id),
        "withheld_count": len(withheld_rows),
        "tracked_count": len(by_id) + len(withheld_rows),
        "review_queue_count": len(queue),
        "critical_review_count": counts["P0_documentary_investigation"],
        "source_identity_review_count": counts["P1_source_identity_review"],
        "technical_retry_count": counts["P2_retry_or_manual_source"],
        "previous_scan_available": previous is not None,
        "new_or_changed_count": sum(q["new_or_changed"] for q in queue),
        "city_summary": sorted(by_city.values(), key=lambda city: city["name"]),
        "queue": queue,
        "withheld": withheld_rows,
    }


def render_markdown(result: dict, *, max_items: int = 30) -> str:
    lines = [
        "# 104-city source review queue",
        "",
        "Source probes are **not proof of venue opening/closure**. "
        "Do not automatically delete objects or mark them visitable. "
        "HTTP 403/429 and network errors are technical follow-ups.",
        "",
        f"Cities: **{result['city_count']}**; active POIs: "
        f"**{result['active_place_count']}**; withheld and still watched: "
        f"**{result['withheld_count']}**.",
        "",
        f"Documentary investigations: **{result['critical_review_count']}**; "
        f"source identity investigations: **{result['source_identity_review_count']}**; "
        f"technical retries: **{result['technical_retry_count']}**.",
        "",
        "## Priority cases and affected prebuilt routes",
        "",
        "| Priority | City | Place | Signal | Routes affected | Source |",
        "|---|---|---|---|---:|---|",
    ]
    for entry in result["queue"][:max_items]:
        source = entry["source_url"]
        lines.append(
            f"| {_clean_cell(entry['priority'])} "
            f"| {_clean_cell(entry['city_name'])} "
            f"| {_clean_cell(entry['title'])} "
            f"| {_clean_cell(entry['signal'])} "
            f"| {entry['route_count']} "
            f"| [source]({source}) |"
        )
    if len(result["queue"]) > max_items:
        lines.append(
            f"\nFull list: {len(result['queue'])} active-place cases, "
            "including every affected route slug, in the JSON artifact."
        )
    lines.extend([
        "",
        "## Withheld objects (not automatically reinstated)",
        "",
    ])
    for entry in result["withheld"]:
        lines.append(
            f"- **{_clean_cell(entry['title'])}** "
            f"({_clean_cell(entry['city_name']) if 'city_name' in entry else _clean_cell(entry['city_slug'])}): "
            f"{_clean_cell(entry['reason'])} — [source]({entry['source_url']})"
        )
    lines.extend([
        "",
        "## Full 104-city coverage",
        "",
        "| City | Active | P0 | Missing | Retry | Operator listing | Undocumented | Withheld |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for city in result["city_summary"]:
        lines.append(
            f"| {_clean_cell(city['name'])} | {city['total']} | "
            f"{city['critical']} | {city['source_missing']} | "
            f"{city['retry']} | {city['operator_listings']} | "
            f"{city['not_documented_by_operator']} | {city['withheld']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scan", required=True)
    parser.add_argument("--previous")
    parser.add_argument("--output", default="place-review-queue.json")
    parser.add_argument("--markdown", default="place-review-queue.md")
    args = parser.parse_args()
    scan = json.loads(Path(args.scan).read_text(encoding="utf-8"))
    prev = (
        json.loads(Path(args.previous).read_text(encoding="utf-8"))
        if args.previous else None
    )
    result = build_review_queue(scan, previous=prev)
    Path(args.output).write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    Path(args.markdown).write_text(render_markdown(result), encoding="utf-8")
    print(
        f"review-queue: cities={result['city_count']} "
        f"active={result['active_place_count']} "
        f"withheld={result['withheld_count']} "
        f"critical={result['critical_review_count']} "
        f"missing={result['source_identity_review_count']} "
        f"retry={result['technical_retry_count']}"
    )


if __name__ == "__main__":
    main()

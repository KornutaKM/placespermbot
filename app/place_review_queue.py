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
from urllib.parse import urlparse

from app.catalog import CityCatalog, list_catalogs
from app.withheld_places import WITHHELD_PLACES

CRITICAL_SIGNALS = frozenset({
    "mapped_inactive_review_required",
    "mapped_access_restriction_review_required",
    "wikidata_end_date_review_required",
})
LOCATION_SIGNALS = frozenset({
    "mapped_coordinates_changed_review_required",
    "mapped_invalid_coordinates_review_required",
})
MISSING_SIGNALS = frozenset({
    "source_missing_review_required",
    "map_feature_missing_review_required",
    "wikidata_item_missing_review_required",
})
REDIRECT_SIGNALS = frozenset({
    "source_insecure_redirect_review_required",
    "source_error_page_review_required",
    "source_cross_host_redirect_review_required",
    "source_generic_home_redirect_review_required",
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
    CRITICAL_SIGNALS | LOCATION_SIGNALS | MISSING_SIGNALS | REDIRECT_SIGNALS
    | RETRY_SIGNALS | PASSIVE_SIGNALS
)


def priority_for_signal(signal: str) -> str | None:
    if signal in CRITICAL_SIGNALS:
        return "P0_documentary_investigation"
    if signal in LOCATION_SIGNALS:
        return "P1_location_review"
    if signal in MISSING_SIGNALS | REDIRECT_SIGNALS:
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
        raise TypeError("Scan must contain a list of places")
    received = [(row.get("city_slug"), row.get("place_slug")) for row in rows]
    if (
        len(received) != len(by_id)
        or len(set(received)) != len(received)
        or set(received) != set(by_id)
        or scan.get("place_count") != len(by_id)
        or scan.get("city_count") != len(active)
    ):
        raise ValueError("Source scan must cover every active place exactly once")
    old_rows = {}
    if previous is not None:
        prior_places = previous.get("places", [])
        if not isinstance(prior_places, list):
            raise ValueError("Previous scan must contain a list of places")
        for prior in prior_places:
            key = (prior["city_slug"], prior["place_slug"])
            if key in old_rows:
                raise ValueError(f"Duplicate place in previous scan: {key}")
            previous_signal = prior.get("probe", {}).get("signal")
            if previous_signal not in ALLOWED_SIGNALS:
                raise ValueError(
                    f"{key}: unknown previous probe signal: {previous_signal}"
                )
            if not isinstance(prior.get("source_url"), str):
                raise ValueError(f"{key}: previous source URL is missing")
            old_rows[key] = prior
    route_impact = defaultdict(list)
    for catalog in active:
        for route in catalog.routes:
            for slug in route.place_slugs:
                route_impact[(catalog.slug, slug)].append(route.slug)

    queue = []
    recovered_technical_probes = []
    source_url_changes = []
    comparable_source_count = 0
    matched_previous_places = 0
    persistent_technical_retry_count = 0
    by_city = {
        catalog.slug: {
            "slug": catalog.slug,
            "name": catalog.name,
            "total": len(catalog.places),
            "critical": 0,
            "source_missing": 0,
            "source_redirect": 0,
            "location_review": 0,
            "retry": 0,
            "operator_listings": 0,
            "official_tourism_listings": 0,
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
        old = old_rows.get(key)
        if old is not None:
            matched_previous_places += 1
        previous_signal = (
            old.get("probe", {}).get("signal") if old is not None else None
        )
        source_changed = (
            old is not None and old.get("source_url") != row["source_url"]
        )
        if source_changed:
            source_url_changes.append({
                "city_slug": catalog.slug,
                "place_slug": place.slug,
                "previous_url": old["source_url"],
                "current_url": row["source_url"],
                "previous_signal": previous_signal,
                "current_signal": signal,
            })
        elif old is not None:
            comparable_source_count += 1
            if previous_signal in RETRY_SIGNALS and signal in RETRY_SIGNALS:
                persistent_technical_retry_count += 1
            if (
                previous_signal in RETRY_SIGNALS
                and signal in PASSIVE_SIGNALS - {"not_probed"}
            ):
                recovered_technical_probes.append({
                    "city_slug": catalog.slug,
                    "place_slug": place.slug,
                    "title": place.title,
                    "source_url": row["source_url"],
                    "source_host": (
                        (urlparse(row["source_url"]).hostname or "")
                        .removeprefix("www.")
                    ),
                    "previous_signal": previous_signal,
                    "current_signal": signal,
                    "route_slugs": sorted(set(route_impact[key])),
                    "meaning": (
                        "previous technical probe failure no longer observed; "
                        "venue and visitor access are NOT verified"
                    ),
                })
        evidence = row.get("published_evidence") or {}
        if evidence.get("status") == "operator_listed":
            by_city[catalog.slug]["operator_listings"] += 1
        else:
            by_city[catalog.slug]["not_documented_by_operator"] += 1
        if evidence.get("status") == "official_tourism_listing":
            by_city[catalog.slug]["official_tourism_listings"] += 1
        priority = priority_for_signal(signal)
        if priority is None:
            continue
        metric = (
            "critical" if signal in CRITICAL_SIGNALS else
            "location_review" if signal in LOCATION_SIGNALS else
            "source_missing" if signal in MISSING_SIGNALS else
            "source_redirect" if signal in REDIRECT_SIGNALS else "retry"
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
            "source_host": (
                (urlparse(place.source.url).hostname or "").removeprefix("www.")
            ),
            "route_slugs": routes,
            "route_count": len(routes),
            "probe_details": row["probe"],
            "operator_evidence": evidence,
            "previous_signal": previous_signal,
            "source_changed_since_previous": source_changed,
            "new_or_changed": (
                previous is not None
                and (previous_signal != signal or source_changed)
            ),
            "disposition": (
                "independent evidence needed; do not delete automatically"
                if signal in CRITICAL_SIGNALS | MISSING_SIGNALS else
                "verify POI coordinates and route stop independently; "
                "do not assume the attraction relocated"
                if signal in LOCATION_SIGNALS else
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
    queue.sort(key=lambda q: (
        q["priority"], not q["new_or_changed"], -q["route_count"],
        q["city_name"], q["title"],
    ))
    # Group shared-host failures: dozens of failed POIs can mean one unreachable
    # source domain, not dozens of physically closed sights.
    retry_by_host = {}
    for entry in queue:
        if entry["priority"] != "P2_retry_or_manual_source":
            continue
        host = entry["source_host"]
        group = retry_by_host.setdefault(host, {
            "host": host,
            "affected_places": 0,
            "city_slugs": set(),
            "route_keys": set(),
            "signals": Counter(),
            "error_types": Counter(),
            "http_statuses": Counter(),
        })
        group["affected_places"] += 1
        group["city_slugs"].add(entry["city_slug"])
        group["route_keys"].update(
            (entry["city_slug"], slug) for slug in entry["route_slugs"]
        )
        group["signals"][entry["signal"]] += 1
        error_type = entry["probe_details"].get("error_type")
        if error_type:
            group["error_types"][error_type] += 1
        code = entry["probe_details"].get("http_status")
        if code is not None:
            group["http_statuses"][str(code)] += 1
    retry_host_summary = sorted(
        (
            {
                "host": item["host"],
                "affected_places": item["affected_places"],
                "affected_city_count": len(item["city_slugs"]),
                "affected_route_count": len(item["route_keys"]),
                "city_slugs": sorted(item["city_slugs"]),
                "signals": dict(sorted(item["signals"].items())),
                "error_types": dict(sorted(item["error_types"].items())),
                "http_statuses": dict(sorted(item["http_statuses"].items())),
                "resolution": (
                    "Investigate DNS, TLS, bot blocking or find another "
                    "independent official source. Do not infer venue closure."
                ),
            }
            for item in retry_by_host.values()
        ),
        key=lambda item: (-item["affected_places"], item["host"]),
    )
    counts = Counter(entry["priority"] for entry in queue)
    recovered_technical_probes.sort(key=lambda entry: (
        entry["source_host"], entry["city_slug"], entry["place_slug"],
    ))
    source_url_changes.sort(key=lambda entry: (
        entry["city_slug"], entry["place_slug"],
    ))
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
        "redirect_review_count": sum(
            item["signal"] in REDIRECT_SIGNALS for item in queue
        ),
        "location_review_count": counts["P1_location_review"],
        "technical_retry_count": counts["P2_retry_or_manual_source"],
        "technical_retry_host_count": len(retry_host_summary),
        "technical_retry_hosts": retry_host_summary,
        "previous_scan_available": previous is not None,
        "previous_scan_place_count": len(old_rows),
        "previous_place_match_count": matched_previous_places,
        "new_places_since_previous_count": (
            len(by_id) - matched_previous_places if previous is not None else 0
        ),
        "retired_places_since_previous_count": (
            len(old_rows) - matched_previous_places if previous is not None else 0
        ),
        "same_source_comparable_count": comparable_source_count,
        "source_url_change_count": len(source_url_changes),
        "source_url_changes": source_url_changes,
        "persistent_technical_retry_count": persistent_technical_retry_count,
        "recovered_technical_probe_count": len(recovered_technical_probes),
        "recovered_technical_probes": recovered_technical_probes,
        "new_or_changed_count": sum(q["new_or_changed"] for q in queue),
        "official_tourism_listing_count": sum(
            city["official_tourism_listings"] for city in by_city.values()
        ),
        "city_summary": sorted(by_city.values(), key=lambda city: city["name"]),
        "queue": queue,
        "withheld": withheld_rows,
    }


def render_markdown(result: dict, *, max_items: int = 30) -> str:
    lines = [
        "# 104-city source review queue",
        "",
        ("Source probes are **not proof of venue opening/closure**. "
        "Do not automatically delete objects or mark them visitable. "
        "HTTP 403/429 and network errors are technical follow-ups."),
        "",
        (f"Cities: **{result['city_count']}**; active POIs: "
        f"**{result['active_place_count']}**; withheld and still watched: "
        f"**{result['withheld_count']}**."),
        "",
        (f"Documentary investigations: **{result['critical_review_count']}**; "
        f"source identity investigations: **{result['source_identity_review_count']}**; "
        f"location review: **{result['location_review_count']}**; "
        f"technical retries: **{result['technical_retry_count']}** "
        f"across **{result['technical_retry_host_count']}** source hosts."),
        "",
        (f"Previous completed scan available: **{result['previous_scan_available']}**; "
        f"new/changed review signals: **{result['new_or_changed_count']}**."),
        (f"Previous snapshot scope: **{result['previous_scan_place_count']}** places; "
        f"matched: **{result['previous_place_match_count']}**; "
        f"added in current catalog: **{result['new_places_since_previous_count']}**; "
        f"absent from current catalog: "
        f"**{result['retired_places_since_previous_count']}**. "
        "New/absent places have no same-URL recovery comparison."),
        (f"Comparable unchanged source URLs: **{result['same_source_comparable_count']}**; "
        f"persistent technical retries: **{result['persistent_technical_retry_count']}**; "
        f"technical probes no longer failing: **{result['recovered_technical_probe_count']}**; "
        f"source URL changes: **{result['source_url_change_count']}**."),
        ("A cleared probe failure only describes the source request. It does "
         "**not** verify a venue, its entrance, or public access. Changed URLs "
         "are excluded from same-source recovery statistics."),
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
        "## Previously failing source requests with no current error",
        "",
        ("Only the technical probe signal cleared; actual visitor access remains "
         "unverified. These rows do not re-enter the active review queue solely "
         "because of their earlier network errors."),
        "",
        "| City | Place | Previous signal | Current signal | Source host |",
        "|---|---|---|---|---|",
    ])
    for entry in result["recovered_technical_probes"][:max_items]:
        lines.append(
            f"| {_clean_cell(entry['city_slug'])} "
            f"| {_clean_cell(entry['title'])} "
            f"| {_clean_cell(entry['previous_signal'])} "
            f"| {_clean_cell(entry['current_signal'])} "
            f"| {_clean_cell(entry['source_host'])} |"
        )
    if len(result["recovered_technical_probes"]) > max_items:
        lines.append(
            "Complete list of cleared technical probes is in the JSON artifact."
        )
    lines.extend([
        "",
        "## Technical retry clusters by source host",
        "",
        ("A single failing website may affect multiple places. Domain failures do "
        "**not** imply these attractions are closed."),
        "",
        "| Source host | Affected POIs | Cities | Routes | Failures |",
        "|---|---:|---:|---:|---|",
    ])
    for item in result["technical_retry_hosts"][:20]:
        counts = ", ".join(
            f"{code}: {number}" for code, number in item["http_statuses"].items()
        )
        counts += ", " if counts and item["error_types"] else ""
        counts += ", ".join(
            f"{error}: {number}" for error, number in item["error_types"].items()
        )
        lines.append(
            f"| {_clean_cell(item['host'])} | {item['affected_places']} "
            f"| {item['affected_city_count']} "
            f"| {item['affected_route_count']} "
            f"| {_clean_cell(counts or 'unspecified')} |"
        )
    if len(result["technical_retry_hosts"]) > 20:
        lines.append(
            "\\nComplete affected-host list is in the review-queue JSON artifact."
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
        "| City | Active | P0 | Location | Missing | Redirect | Retry | Operator listing | Tourism office | No operator proof | Withheld |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for city in result["city_summary"]:
        lines.append(
            f"| {_clean_cell(city['name'])} | {city['total']} | "
            f"{city['critical']} | {city['location_review']} | "
            f"{city['source_missing']} | {city['source_redirect']} "
            f"| {city['retry']} | "
            f"{city['operator_listings']} | "
            f"{city['official_tourism_listings']} | "
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
        f"location={result['location_review_count']} "
        f"retry={result['technical_retry_count']} "
        f"retry_hosts={result['technical_retry_host_count']}"
    )


if __name__ == "__main__":
    main()

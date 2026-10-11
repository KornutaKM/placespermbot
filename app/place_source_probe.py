"""Live documentary/source drift probes for every registered POI.

Run only from maintenance CI, never from FastAPI or Telegram requests.
A responsive URL or an OSM feature is NOT proof a place is operating.
Transport failures, CAPTCHA, deletion of a map item and lifecycle tags
produce review signals, never automatic deletion or active certification.
"""
from __future__ import annotations

import argparse
import json
import re
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from app.catalog import list_catalogs
from app.place_evidence import public_evidence
from app.withheld_places import WITHHELD_PLACES

USER_AGENT = "PlacesBotSourceAudit/1.0 (public tourism source maintenance)"
OSM_URL = re.compile(r"^https://www\.openstreetmap\.org/(node|way|relation)/(\d+)$")
WIKIDATA_URL = re.compile(r"^https://www\.wikidata\.org/wiki/(Q[1-9]\d*)$")
MAP_LIFECYCLE = frozenset(("disused", "abandoned", "demolished", "removed",
                           "destroyed", "razed", "proposed", "construction"))
PAGE_WORKERS = 8


def classify_url(url: str) -> tuple[str, str, str]:
    match = OSM_URL.fullmatch(url)
    if match:
        return "osm", match[1], match[2]
    match = WIKIDATA_URL.fullmatch(url)
    if match:
        return "wikidata", "entity", match[1]
    return "web", "page", url


def http_transport_url(url: str) -> str:
    """Percent-encode IRI paths/queries; don't treat Unicode URLs as dead sites."""
    parts = urlsplit(url)
    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username is not None
        or parts.password is not None
    ):
        raise ValueError("Probe source must be a public HTTPS URL")
    hostname = parts.hostname.encode("idna").decode("ascii")
    if ":" in hostname:
        hostname = f"[{hostname}]"
    if parts.port is not None:
        hostname += f":{parts.port}"
    # Existing percent escapes must not be encoded again. A fragment is local
    # browser state and must never be part of an outbound HTTP request.
    path = quote(parts.path, safe="/%:@!$&'()*+,;=-._~")
    query = quote(parts.query, safe="/%:@!$&'()*+,;=?-._~")
    return urlunsplit((parts.scheme, hostname, path, query, ""))


def http_request(url: str, *, timeout: float, method: str = "GET"):
    request = Request(
        http_transport_url(url),
        method=method,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json, application/xml, text/html, */*",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        content = response.read(1024 * 1024) if method == "GET" else b""
        return response.status, response.geturl(), content


def _status(code: int, kind: str) -> str:
    if 200 <= code < 400:
        return "source_reachable_not_venue_verified"
    if code in (401, 403, 405, 429):
        return "probe_blocked_or_throttled"
    if code in (404, 410):
        return "source_missing_review_required"
    return "probe_inconclusive"


def probe_page(url: str, *, timeout: float = 12) -> dict:
    """URL-level availability only. Treat 403/5xx and timeouts as inconclusive."""
    try:
        transport_url = http_transport_url(url)
        try:
            status, final, _ = http_request(url, timeout=timeout, method="HEAD")
            if status == 405:
                status, final, _ = http_request(url, timeout=timeout)
        except HTTPError as exc:
            if exc.code == 405:
                status, final, _ = http_request(url, timeout=timeout)
            else:
                return {
                    "signal": _status(exc.code, "web"),
                    "http_status": exc.code,
                    "redirected_to": None,
                }
        return {
            "signal": _status(status, "web"),
            "http_status": status,
            "redirected_to": final if final not in (url, transport_url) else None,
        }
    except HTTPError as exc:
        return {
            "signal": _status(exc.code, "web"),
            "http_status": exc.code, "redirected_to": None,
        }
    except (OSError, URLError, ValueError) as exc:
        return {
            "signal": "probe_inconclusive", "http_status": None,
            "error_type": type(exc).__name__,
        }


def osm_lifecycle_signal(tags: dict[str, str]) -> str:
    for key, value in tags.items():
        prefix = key.split(":", 1)[0]
        if prefix in MAP_LIFECYCLE or value in ("demolished", "abandoned", "disused"):
            return "mapped_inactive_review_required"
        if key == "access" and value in ("no", "private"):
            return "mapped_access_restriction_review_required"
    return "map_feature_present_not_venue_verified"


def probe_osm_batch(
    entity_type: str, entity_ids: list[str], *, timeout: float = 50,
) -> dict[str, dict]:
    """OSM API multi-fetch; missing map feature is NOT proof of demolition."""
    plural = {"node": "nodes", "way": "ways", "relation": "relations"}[entity_type]
    url = (
        f"https://api.openstreetmap.org/api/0.6/{plural}?"
        + urlencode({plural: ",".join(entity_ids)})
    )
    result = {}
    try:
        _, _, body = http_request(url, timeout=timeout)
        root = ET.fromstring(body)
        found = {}
        for elem in root.findall(entity_type):
            entity_id = elem.get("id")
            if entity_id is None:
                continue
            tags = {e.get("k", ""): e.get("v", "")
                    for e in elem.findall("tag") if e.get("k")}
            row = {
                "signal": osm_lifecycle_signal(tags),
                "map_name": tags.get("name:ru") or tags.get("name"),
                "map_access": tags.get("access"),
                "map_lifecycle": {
                    k: v for k, v in tags.items()
                    if k.split(":", 1)[0] in MAP_LIFECYCLE
                },
                "last_osm_edit": elem.get("timestamp"),
            }
            if entity_type == "node":
                row["map_lat"] = elem.get("lat")
                row["map_lon"] = elem.get("lon")
            found[entity_id] = row
        for entity_id in entity_ids:
            result[entity_id] = found.get(entity_id, {
                "signal": "map_feature_missing_review_required"
            })
    except (HTTPError, URLError, OSError, ET.ParseError, ValueError) as exc:
        for entity_id in entity_ids:
            result[entity_id] = {
                "signal": "probe_inconclusive",
                "error_type": type(exc).__name__,
            }
    return result


def probe_wikidata(qids: list[str], *, timeout: float = 35) -> dict[str, dict]:
    """Wikidata entity metadata; a historical P576 is a flag, not final proof."""
    results = {}
    for start in range(0, len(qids), 40):
        batch = qids[start:start + 40]
        url = "https://www.wikidata.org/w/api.php?" + urlencode({
            "action": "wbgetentities", "ids": "|".join(batch),
            "props": "info|claims|labels", "languages": "ru|en",
            "format": "json",
        })
        try:
            _, _, body = http_request(url, timeout=timeout)
            entities = json.loads(body)["entities"]
            for qid in batch:
                obj = entities.get(qid, {})
                if obj.get("missing") or not obj:
                    results[qid] = {
                        "signal": "wikidata_item_missing_review_required"
                    }
                    continue
                claims = obj.get("claims", {})
                results[qid] = {
                    "signal": (
                        "wikidata_end_date_review_required"
                        if "P576" in claims
                        else "wikidata_item_present_not_venue_verified"
                    ),
                    "wikidata_lastrevid": obj.get("lastrevid"),
                    "wikidata_p576_present": "P576" in claims,
                    "wikidata_name": (
                        obj.get("labels", {}).get("ru")
                        or obj.get("labels", {}).get("en")
                        or {}
                    ).get("value"),
                }
        except (HTTPError, URLError, OSError, ValueError, KeyError) as exc:
            for qid in batch:
                results[qid] = {
                    "signal": "probe_inconclusive",
                    "error_type": type(exc).__name__,
                }
    return results


def run_audit(*, live: bool = False, timeout: float = 12) -> dict:
    """Return one record for every POI in every city, no silent omissions."""
    catalogs = list_catalogs()
    original = defaultdict(list)
    for city in catalogs:
        for place in city.places:
            original[place.source.url].append((city, place))
    unique = list(original)
    result_by_url: dict[str, dict] = {}
    if live:
        # Site URLs are deduplicated. This tests the *citation*, not the place.
        pages = [url for url in unique if classify_url(url)[0] == "web"]
        with ThreadPoolExecutor(max_workers=PAGE_WORKERS) as executor:
            tasks = {
                executor.submit(probe_page, url, timeout=timeout): url
                for url in pages
            }
            for future in as_completed(tasks):
                url = tasks[future]
                try:
                    result_by_url[url] = future.result()
                except (OSError, ValueError, RuntimeError, TypeError) as exc:
                    result_by_url[url] = {
                        "signal": "probe_inconclusive",
                        "error_type": type(exc).__name__,
                    }
        # Multi-fetch actual OSM object metadata in bounded batches.
        for kind in ("node", "way", "relation"):
            pairs = [
                (url, id_) for url in unique
                if (parts := classify_url(url))[0] == "osm"
                and parts[1] == kind for id_ in (parts[2],)
            ]
            for start in range(0, len(pairs), 60):
                batch = pairs[start:start + 60]
                found = probe_osm_batch(
                    kind, [entity_id for _, entity_id in batch],
                    timeout=max(timeout, 40),
                )
                for url, entity_id in batch:
                    result_by_url[url] = found[entity_id]
                time.sleep(0.4)
        pairs = [
            (url, parts[2]) for url in unique
            if (parts := classify_url(url))[0] == "wikidata"
        ]
        wiki = probe_wikidata([qid for _, qid in pairs], timeout=max(timeout, 30))
        for url, qid in pairs:
            result_by_url[url] = wiki[qid]
    # Continue watching withheld sites so they can be reviewed for reinstatement.
    withheld_watch = []
    for item in WITHHELD_PLACES:
        kind, subtype, identifier = classify_url(item.map_url)
        if live and kind == "osm":
            evidence = probe_osm_batch(
                subtype, [identifier], timeout=max(timeout, 40)
            )[identifier]
        else:
            evidence = {"signal": "not_probed"}
        withheld_watch.append({
            "city_slug": item.city_slug,
            "place_slug": item.place_slug,
            "title": item.title,
            "source_url": item.map_url,
            "reason": item.reason,
            "probe": evidence,
            "eligibility": "withheld_pending_independent_opening_evidence",
        })
    rows = []
    city_stats: dict[str, Counter] = defaultdict(Counter)
    for city in catalogs:
        for place in city.places:
            kind, _, _ = classify_url(place.source.url)
            live_result = result_by_url.get(place.source.url, {
                "signal": "not_probed"
            })
            row = {
                "city_slug": city.slug,
                "city_name": city.name,
                "place_slug": place.slug,
                "title": place.title,
                "category": place.category,
                "source_url": place.source.url,
                "source_kind": kind,
                "source_recorded_on": place.source.checked_at.isoformat(),
                "published_evidence": public_evidence(city.slug, place.slug),
                "probe": live_result,
                "reality_status": "not_proven_by_automated_source_probe",
            }
            rows.append(row)
            city_stats[city.slug]["total"] += 1
            city_stats[city.slug][live_result["signal"]] += 1
    status_counts = Counter(item["probe"]["signal"] for item in rows)
    return {
        "date": datetime.now(UTC).isoformat(),
        "probe_mode": "live" if live else "offline_structure_only",
        "meaning": "URL and mapping drift signals; no real-world current POI "
                   "existence, entrance, hours, transport or public access certification",
        "city_count": len(catalogs),
        "place_count": len(rows),
        "withheld_count": len(withheld_watch),
        "total_tracked": len(rows) + len(withheld_watch),
        "unique_source_urls": len({
            *unique, *(item["source_url"] for item in withheld_watch)
        }),
        "signal_counts": dict(sorted(status_counts.items())),
        "city_summary": [
            {"slug": c.slug, "name": c.name, **dict(city_stats[c.slug])}
            for c in catalogs
        ],
        "places": rows,
        "withheld_review_watch": withheld_watch,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true",
                        help="Probe public web and map APIs; never run in app process")
    parser.add_argument("--timeout", type=float, default=12)
    parser.add_argument("--output", default="-")
    args = parser.parse_args()
    report = run_audit(live=args.live, timeout=args.timeout)
    result = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output == "-":
        print(result, end="")
    else:
        with open(args.output, "w", encoding="utf-8") as stream:
            stream.write(result)
    print(
        "source-probe: cities={city_count} places={place_count} "
        "unique_urls={unique_source_urls} mode={probe_mode} "
        "signals={signal_counts}".format(**report),
        file=__import__("sys").stderr,
    )


if __name__ == "__main__":
    main()

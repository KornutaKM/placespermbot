"""Advisory audits for distances and visit times of editorial city routes."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

from app.catalog import CityCatalog, list_catalogs
from app.route_safety import route_geography


@dataclass(frozen=True, slots=True)
class RouteFinding:
    city: str
    route: str
    code: str
    first_stop: str
    next_stop: str
    measured_km: float
    declared_km: float


HARD_ROUTE_CODES = frozenset({
    "distance_below_geodesic_minimum",
    "duration_below_visit_time",
})


def hard_route_findings(findings: tuple[RouteFinding, ...]) -> tuple[RouteFinding, ...]:
    """Leave long/transit legs advisory; fail on impossible advertised metrics."""
    return tuple(item for item in findings if item.code in HARD_ROUTE_CODES)


def inspect_routes(catalog: CityCatalog) -> tuple[RouteFinding, ...]:
    """Report only measurable inconsistencies; don't infer roads or ETAs."""
    places = {place.slug: place for place in catalog.places}
    findings = []
    for route in catalog.routes:
        ordered = tuple(places[slug] for slug in route.place_slugs if slug in places)
        geography = route_geography(ordered)
        for first, second, distance in geography.long_legs:
            findings.append(
                RouteFinding(
                    catalog.slug, route.slug, "long_straight_line_leg",
                    first, second, distance, route.distance_km,
                )
            )
        if (
            len(ordered) == len(route.place_slugs)
            and geography.straight_line_km > route.distance_km + 0.5
        ):
            findings.append(
                RouteFinding(
                    catalog.slug, route.slug, "distance_below_geodesic_minimum",
                    "", "", geography.straight_line_km, route.distance_km,
                )
            )
        if (
            len(ordered) == len(route.place_slugs)
            and sum(place.visit_minutes for place in ordered) > route.duration_minutes
        ):
            findings.append(
                RouteFinding(
                    catalog.slug, route.slug, "duration_below_visit_time",
                    "", "", 0.0, route.distance_km,
                )
            )
    return tuple(findings)


def collect_route_findings() -> tuple[RouteFinding, ...]:
    return tuple(sorted(
        (finding for catalog in list_catalogs() for finding in inspect_routes(catalog)),
        key=lambda item: (item.city, item.route, item.code, item.first_stop),
    ))


def render_route_review(findings: tuple[RouteFinding, ...]) -> str:
    lines = [
        "## Editorial route geography review (advisory)",
        "",
        "Geodesic distances are lower bounds, not walking routes or time estimates.",
        f"Potential issues to review: {len(findings)}",
        "",
        "| City | Route | Signal | Segment | Straight-line km | Declared km |",
        "|---|---|---|---|---:|---:|",
    ]
    for finding in findings:
        segment = (
            f"{finding.first_stop} → {finding.next_stop}"
            if finding.first_stop else "all stops"
        )
        lines.append(
            f"| {finding.city} | {finding.route} | {finding.code} | "
            f"{segment} | {finding.measured_km:.1f} | {finding.declared_km:g} |"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument(
        "--check", action="store_true",
        help="Fail only on impossible duration/distance metrics; long legs remain advisory",
    )
    args = parser.parse_args(argv)
    findings = collect_route_findings()
    if args.format == "json":
        print(json.dumps([asdict(item) for item in findings], ensure_ascii=False, indent=2))
    else:
        print(render_route_review(findings))
    if args.check and hard_route_findings(findings):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

"""Deterministic cross-city coverage diagnostics (advisory, not a quality gate)."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from urllib.parse import urlparse

from app.catalog import CityCatalog, coordinates_distance_km, list_catalogs


@dataclass(frozen=True, slots=True)
class CityCoverage:
    city: str
    name: str
    places: int
    routes: int
    districts: int
    categories: int
    free_places: int
    family_places: int
    museums: int
    source_domains: int
    places_used_by_routes: int
    route_coverage_percent: int
    single_stop_routes: int
    max_consecutive_leg_km: float
    signals: tuple[str, ...]


def assess_catalog_coverage(catalog: CityCatalog) -> CityCoverage:
    """Describe discovery gaps without conflating them with validation failures."""
    place_by_slug = {place.slug: place for place in catalog.places}
    used_slugs = set()
    max_leg_km = 0.0
    one_stop = 0

    for route in catalog.routes:
        if len(route.place_slugs) == 1:
            one_stop += 1
        for slug in route.place_slugs:
            if slug in place_by_slug:
                used_slugs.add(slug)
        for first_slug, second_slug in zip(
            route.place_slugs, route.place_slugs[1:]
        ):
            first = place_by_slug.get(first_slug)
            second = place_by_slug.get(second_slug)
            if first is not None and second is not None:
                leg_km = coordinates_distance_km(
                    first.latitude,
                    first.longitude,
                    second.latitude,
                    second.longitude,
                )
                max_leg_km = max(max_leg_km, leg_km)

    places = len(catalog.places)
    categories = len({place.category for place in catalog.places})
    family = sum("с детьми" in place.tags for place in catalog.places)
    source_domains = {
        (urlparse(place.source.url).hostname or "").removeprefix("www.")
        for place in catalog.places
    } - {""}
    coverage = round(100 * len(used_slugs) / places) if places else 0
    signals = []
    if places < 20:
        signals.append("small_catalog")
    if categories < 5:
        signals.append("category_gap")
    if family < 8:
        signals.append("limited_family_options")
    if len(source_domains) < 2:
        signals.append("single_source_domain")
    if coverage < 60:
        signals.append("low_route_coverage")
    if one_stop:
        signals.append("single_stop_routes")
    if max_leg_km > 12:
        signals.append("long_route_leg_review")

    return CityCoverage(
        city=catalog.slug,
        name=catalog.name,
        places=places,
        routes=len(catalog.routes),
        districts=len({place.district for place in catalog.places}),
        categories=categories,
        free_places=sum(place.is_free for place in catalog.places),
        family_places=family,
        museums=sum(place.category == "museums" for place in catalog.places),
        source_domains=len(source_domains),
        places_used_by_routes=len(used_slugs),
        route_coverage_percent=coverage,
        single_stop_routes=one_stop,
        max_consecutive_leg_km=round(max_leg_km, 2),
        signals=tuple(signals),
    )


def collect_coverage() -> tuple[CityCoverage, ...]:
    """Place cities with the most advisory signals at the top."""
    rows = (assess_catalog_coverage(catalog) for catalog in list_catalogs())
    return tuple(sorted(rows, key=lambda row: (-len(row.signals), row.places, row.city)))


def render_coverage_markdown(rows: tuple[CityCoverage, ...]) -> str:
    header = [
        "## City catalog coverage (advisory)",
        "",
        "Coverage and signals guide editorial work; they are not CI failures.",
        "",
        "| City | Places | Routes | Districts | Categories | Family | Source domains "
        "| Route reach | Longest leg km | Signals |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        signals = ", ".join(row.signals) or "—"
        header.append(
            f"| {row.name} | {row.places} | {row.routes} | "
            f"{row.districts} | {row.categories} | {row.family_places} | "
            f"{row.source_domains} | {row.route_coverage_percent}% | "
            f"{row.max_consecutive_leg_km:.2f} | {signals} |"
        )
    return "\n".join(header)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args(argv)
    rows = collect_coverage()
    if args.format == "json":
        print(json.dumps([asdict(row) for row in rows], ensure_ascii=False, indent=2))
    else:
        print(render_coverage_markdown(rows))


if __name__ == "__main__":
    main()

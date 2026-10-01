from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse

from app.catalog import CityCatalog

MAX_SOURCE_AGE_DAYS = 366
KNOWN_IRRELEVANT_SOURCE_PATHS = (
    "/tourism/lechebnaya-verkhovaya-ezda/",
    "/pervouralsk/",
)


@dataclass(frozen=True, slots=True)
class CatalogIssue:
    code: str
    message: str


def validate_catalog(catalog: CityCatalog) -> tuple[CatalogIssue, ...]:
    issues: list[CatalogIssue] = []
    place_slugs: set[str] = set()
    route_slugs: set[str] = set()

    if not catalog.slug.strip():
        issues.append(CatalogIssue("city.slug.empty", "City slug must not be empty."))
    if not catalog.name.strip():
        issues.append(CatalogIssue("city.name.empty", "City name must not be empty."))
    if not catalog.category_labels:
        issues.append(
            CatalogIssue(
                "city.categories.empty",
                f"{catalog.slug or '<empty>'}: category labels must not be empty",
            )
        )
    for category, label in catalog.category_labels.items():
        if not category.strip():
            issues.append(
                CatalogIssue(
                    "city.category.slug.empty",
                    f"{catalog.slug or '<empty>'}: category slug must not be empty",
                )
            )
        if not label.strip():
            issues.append(
                CatalogIssue(
                    "city.category.label.empty",
                    f"{catalog.slug or '<empty>'}: category label must not be empty",
                )
            )
    if not catalog.places:
        issues.append(
            CatalogIssue(
                "city.places.empty",
                f"{catalog.slug or '<empty>'}: catalog must contain places",
            )
        )
    if not catalog.routes:
        issues.append(
            CatalogIssue(
                "city.routes.empty",
                f"{catalog.slug or '<empty>'}: catalog must contain routes",
            )
        )

    for place in catalog.places:
        if place.slug in place_slugs:
            issues.append(CatalogIssue("place.slug.duplicate", f"Duplicate place slug: {place.slug}"))
        place_slugs.add(place.slug)

        if not place.slug.strip():
            issues.append(
                CatalogIssue("place.slug.empty", "Place slug must not be empty")
            )
        if not place.title.strip():
            issues.append(
                CatalogIssue("place.title.empty", f"{place.slug}: title must not be empty")
            )
        if not place.summary.strip():
            issues.append(
                CatalogIssue(
                    "place.summary.empty",
                    f"{place.slug}: summary must not be empty",
                )
            )
        if not place.district.strip():
            issues.append(
                CatalogIssue(
                    "place.district.empty",
                    f"{place.slug}: district must not be empty",
                )
            )
        if not place.emoji.strip():
            issues.append(
                CatalogIssue("place.emoji.empty", f"{place.slug}: emoji must not be empty")
            )
        if not place.tags:
            issues.append(
                CatalogIssue("place.tags.empty", f"{place.slug}: tags must not be empty")
            )
        elif any(not tag.strip() for tag in place.tags):
            issues.append(
                CatalogIssue(
                    "place.tag.empty",
                    f"{place.slug}: tags must not contain empty values",
                )
            )
        elif len(place.tags) != len(set(place.tags)):
            issues.append(
                CatalogIssue(
                    "place.tag.duplicate",
                    f"{place.slug}: tags must be unique",
                )
            )

        if place.category not in catalog.category_labels:
            issues.append(
                CatalogIssue(
                    "place.category.unknown",
                    f"{place.slug}: unknown category {place.category}",
                )
            )
        if place.visit_minutes <= 0:
            issues.append(CatalogIssue("place.visit.invalid", f"{place.slug}: visit time must be positive"))
        if not -90 <= place.latitude <= 90 or not -180 <= place.longitude <= 180:
            issues.append(CatalogIssue("place.coordinates.invalid", f"{place.slug}: invalid coordinates"))
        parsed = urlparse(place.source.url)
        if parsed.scheme != "https" or not parsed.netloc:
            issues.append(CatalogIssue("place.source.invalid", f"{place.slug}: source must be an HTTPS URL"))
        if not place.source.name.strip():
            issues.append(CatalogIssue("place.source.name.empty", f"{place.slug}: source name must not be empty"))
        today = datetime.now(UTC).date()
        if place.source.checked_at > today:
            issues.append(CatalogIssue("place.source.checked_at.future", f"{place.slug}: source check date is in the future"))
        elif (today - place.source.checked_at).days > MAX_SOURCE_AGE_DAYS:
            issues.append(CatalogIssue("place.source.checked_at.stale", f"{place.slug}: source verification is stale"))
        if any(path in parsed.path for path in KNOWN_IRRELEVANT_SOURCE_PATHS):
            issues.append(CatalogIssue("place.source.irrelevant", f"{place.slug}: source URL is known to be unrelated"))

    for route in catalog.routes:
        if route.slug in route_slugs:
            issues.append(CatalogIssue("route.slug.duplicate", f"Duplicate route slug: {route.slug}"))
        route_slugs.add(route.slug)

        if not route.slug.strip():
            issues.append(CatalogIssue("route.slug.empty", "Route slug must not be empty"))
        if not route.title.strip():
            issues.append(
                CatalogIssue("route.title.empty", f"{route.slug}: title must not be empty")
            )
        if not route.summary.strip():
            issues.append(
                CatalogIssue(
                    "route.summary.empty",
                    f"{route.slug}: summary must not be empty",
                )
            )
        if route.duration_minutes <= 0 or route.distance_km <= 0:
            issues.append(
                CatalogIssue(
                    "route.metrics.invalid",
                    f"{route.slug}: route metrics must be positive",
                )
            )
        if not route.place_slugs:
            issues.append(CatalogIssue("route.empty", f"{route.slug}: route must contain places"))
        missing = set(route.place_slugs) - place_slugs
        if missing:
            issues.append(
                CatalogIssue(
                    "route.place.missing",
                    f"{route.slug}: unknown places: {', '.join(sorted(missing))}",
                )
            )
        if len(route.place_slugs) != len(set(route.place_slugs)):
            issues.append(CatalogIssue("route.place.duplicate", f"{route.slug}: duplicate route stops"))

    return tuple(issues)


def validate_catalogs(catalogs: tuple[CityCatalog, ...]) -> tuple[CatalogIssue, ...]:
    issues: list[CatalogIssue] = []
    city_slugs: set[str] = set()
    for catalog in catalogs:
        if catalog.slug in city_slugs:
            issues.append(CatalogIssue("city.slug.duplicate", f"Duplicate city slug: {catalog.slug}"))
        city_slugs.add(catalog.slug)
        issues.extend(validate_catalog(catalog))
    return tuple(issues)

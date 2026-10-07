from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from app.catalog import get_catalog
from app.catalog_quality import validate_catalog_quality
from app.catalog_validation import CatalogIssue, validate_catalog
from app.city_manifest import list_city_manifests


@dataclass(frozen=True, slots=True)
class CatalogAudit:
    slug: str
    name: str
    places: int
    routes: int
    districts: int
    categories: int
    free_places: int
    family_places: int
    museums: int
    source_domains: tuple[str, ...]
    oldest_source_checked_at: str
    newest_source_checked_at: str
    issues: tuple[CatalogIssue, ...]


def collect_catalog_audits() -> tuple[CatalogAudit, ...]:
    audits = []
    for manifest in list_city_manifests():
        catalog = get_catalog(manifest.slug)
        source_dates = tuple(place.source.checked_at for place in catalog.places)
        source_domains = tuple(
            sorted(
                {
                    urlparse(place.source.url).hostname or ""
                    for place in catalog.places
                }
                - {""}
            )
        )
        issues = (
            validate_catalog(catalog)
            + validate_catalog_quality(catalog, manifest.quality)
        )
        audits.append(
            CatalogAudit(
                slug=catalog.slug,
                name=catalog.name,
                places=len(catalog.places),
                routes=len(catalog.routes),
                districts=len({place.district for place in catalog.places}),
                categories=len({place.category for place in catalog.places}),
                free_places=sum(place.is_free for place in catalog.places),
                family_places=sum(
                    "с детьми" in place.tags for place in catalog.places
                ),
                museums=sum(
                    place.category == "museums" for place in catalog.places
                ),
                source_domains=source_domains,
                oldest_source_checked_at=min(source_dates).isoformat(),
                newest_source_checked_at=max(source_dates).isoformat(),
                issues=issues,
            )
        )
    return tuple(sorted(audits, key=lambda audit: audit.name))


def render_catalog_audit(audits: tuple[CatalogAudit, ...]) -> str:
    lines = []
    total_places = sum(audit.places for audit in audits)
    total_routes = sum(audit.routes for audit in audits)
    issue_count = sum(len(audit.issues) for audit in audits)
    lines.append(
        "catalog-audit: "
        f"cities={len(audits)} places={total_places} routes={total_routes} "
        f"issues={issue_count}"
    )

    for audit in audits:
        status = "ok" if not audit.issues else f"issues={len(audit.issues)}"
        lines.append(
            f"{audit.slug}: {status} "
            f"places={audit.places} routes={audit.routes} "
            f"districts={audit.districts} categories={audit.categories} "
            f"free={audit.free_places} family={audit.family_places} "
            f"museums={audit.museums} sources={len(audit.source_domains)} "
            f"source_age={audit.oldest_source_checked_at}.."
            f"{audit.newest_source_checked_at}"
        )
        for issue in audit.issues:
            lines.append(f"  - {issue.code}: {issue.message}")

    return "\n".join(lines)


def main() -> None:
    audits = collect_catalog_audits()
    print(render_catalog_audit(audits))
    if any(audit.issues for audit in audits):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

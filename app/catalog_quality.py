from __future__ import annotations

from app.catalog import CityCatalog
from app.catalog_validation import CatalogIssue
from app.city_manifest import CatalogQualityProfile


def validate_catalog_quality(
    catalog: CityCatalog,
    profile: CatalogQualityProfile,
) -> tuple[CatalogIssue, ...]:
    metrics = {
        "places": len(catalog.places),
        "routes": len(catalog.routes),
        "districts": len({place.district for place in catalog.places}),
        "categories": len({place.category for place in catalog.places}),
        "free_places": sum(place.is_free for place in catalog.places),
        "family_places": sum("с детьми" in place.tags for place in catalog.places),
        "museums": sum(place.category == "museums" for place in catalog.places),
    }
    minimums = {
        "places": profile.min_places,
        "routes": profile.min_routes,
        "districts": profile.min_districts,
        "categories": profile.min_categories,
        "free_places": profile.min_free_places,
        "family_places": profile.min_family_places,
        "museums": profile.min_museums,
    }

    issues = []
    for metric, minimum in minimums.items():
        actual = metrics[metric]
        if actual < minimum:
            issues.append(
                CatalogIssue(
                    f"quality.{metric}.low",
                    f"{catalog.slug}: {metric}={actual}, required>={minimum}",
                )
            )
    return tuple(issues)

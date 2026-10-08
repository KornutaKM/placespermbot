from app.catalog import get_catalog
from app.catalog_audit import collect_catalog_audits, render_catalog_audit
from app.catalog_quality import validate_catalog_quality
from app.city_manifest import CatalogQualityProfile, list_city_manifests


def test_catalog_audit_accepts_all_registered_cities() -> None:
    audits = collect_catalog_audits()

    assert len(audits) == len(list_city_manifests())
    assert all(not audit.issues for audit in audits)
    assert all(audit.places > 0 for audit in audits)
    assert all(audit.routes > 0 for audit in audits)
    assert all(audit.source_domains for audit in audits)
    assert all(audit.oldest_source_checked_at for audit in audits)
    assert all(audit.newest_source_checked_at for audit in audits)


def test_catalog_audit_render_includes_global_and_city_metrics() -> None:
    audits = collect_catalog_audits()
    rendered = render_catalog_audit(audits)

    assert f"cities={len(audits)}" in rendered
    assert f"places={sum(audit.places for audit in audits)}" in rendered
    assert "issues=0" in rendered
    assert "saint-petersburg: ok" in rendered
    assert "chelyabinsk: ok" in rendered


def test_quality_validator_reports_every_shortfall() -> None:
    catalog = get_catalog("sochi")
    profile = CatalogQualityProfile(
        min_places=999,
        min_routes=999,
        min_districts=999,
        min_categories=999,
        min_free_places=999,
        min_family_places=999,
        min_museums=999,
    )

    codes = {
        issue.code
        for issue in validate_catalog_quality(catalog, profile)
    }

    assert codes == {
        "quality.places.low",
        "quality.routes.low",
        "quality.districts.low",
        "quality.categories.low",
        "quality.free_places.low",
        "quality.family_places.low",
        "quality.museums.low",
    }

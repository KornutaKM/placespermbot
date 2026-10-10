"""Release metadata contract: catalog registry, README and production baseline."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from app.catalog import list_catalogs
from app.city_manifest import list_city_manifests
from app.deployment_preflight import MINIMUM_CITY_COUNT

CITY_COUNT_RE = re.compile(
    r"Поддерживаются\s+\*\*(\d+)\s+город(?:а|ов)?\*\*\."
)


@dataclass(frozen=True, slots=True)
class ReleaseConsistency:
    status: str
    registered_cities: int
    documented_cities: int | None
    production_minimum_cities: int
    issues: tuple[str, ...]


def assess_release_consistency(
    readme: str,
    *,
    registered_cities: int,
    manifest_cities: int,
    production_minimum_cities: int,
) -> ReleaseConsistency:
    """Do not mask stale release declarations by automatically rewriting them."""
    matches = CITY_COUNT_RE.findall(readme)
    documented = int(matches[0]) if len(matches) == 1 else None
    issues = []
    if documented is None:
        issues.append("readme_city_count_missing_or_ambiguous")
    elif documented != registered_cities:
        issues.append("readme_city_count_mismatch")
    if manifest_cities != registered_cities:
        issues.append("manifest_city_count_mismatch")
    if production_minimum_cities != registered_cities:
        issues.append("production_minimum_city_count_mismatch")
    if registered_cities < 1:
        issues.append("empty_catalog_registry")
    return ReleaseConsistency(
        status="ready" if not issues else "inconsistent",
        registered_cities=registered_cities,
        documented_cities=documented,
        production_minimum_cities=production_minimum_cities,
        issues=tuple(issues),
    )


def collect_release_consistency(readme_path: str | Path) -> ReleaseConsistency:
    """Read a local document; never read .env, secrets or user data."""
    readme = Path(readme_path).read_text(encoding="utf-8")
    return assess_release_consistency(
        readme,
        registered_cities=len(list_catalogs()),
        manifest_cities=len(list_city_manifests()),
        production_minimum_cities=MINIMUM_CITY_COUNT,
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readme", default="README.md")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    report = collect_release_consistency(args.readme)
    print(json.dumps(asdict(report), ensure_ascii=False, sort_keys=True))
    if args.check and report.issues:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

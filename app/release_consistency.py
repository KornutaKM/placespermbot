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
CITY_NAMES_RE = re.compile(r"\*\*([^*\n]+)\*\*")
GUIDE_CITY_MINIMUM_RE = re.compile(r"--min-cities\s+(\d+)\b")


def _readme_city_names(readme: str) -> tuple[str, ...] | None:
    """Read the explicit city bullets, not unrelated bold text elsewhere."""
    sections = re.findall(r"(?ms)^## Города\s*$\n(.*?)(?=^## |\Z)", readme)
    if len(sections) != 1 or sections[0].count("Сейчас доступны:") != 1:
        return None

    city_text = sections[0].split("Сейчас доступны:", 1)[1]
    names: list[str] = []
    started = False
    for line in city_text.splitlines():
        if line.startswith("- "):
            started = True
            line_names = CITY_NAMES_RE.findall(line)
            if not line_names:
                return None
            names.extend(line_names)
        elif started or line.strip():
            break
    return tuple(names) if names else None


@dataclass(frozen=True, slots=True)
class ReleaseConsistency:
    status: str
    registered_cities: int
    documented_cities: int | None
    documented_city_names: tuple[str, ...] | None
    production_minimum_cities: int
    deployment_guide_minimum_cities: int | None
    issues: tuple[str, ...]


def assess_release_consistency(
    readme: str,
    *,
    deployment_guide: str,
    registered_cities: int,
    manifest_city_names: tuple[str, ...],
    production_minimum_cities: int,
) -> ReleaseConsistency:
    """Do not mask stale release declarations by automatically rewriting them."""
    count_matches = CITY_COUNT_RE.findall(readme)
    documented = int(count_matches[0]) if len(count_matches) == 1 else None
    names = _readme_city_names(readme)
    guide_matches = GUIDE_CITY_MINIMUM_RE.findall(deployment_guide)
    guide_minimum = int(guide_matches[0]) if len(guide_matches) == 1 else None

    issues: list[str] = []
    if documented is None:
        issues.append("readme_city_count_missing_or_ambiguous")
    elif documented != registered_cities:
        issues.append("readme_city_count_mismatch")
    if names is None:
        issues.append("readme_city_list_missing_or_ambiguous")
    else:
        if len(names) != len(set(names)):
            issues.append("readme_city_list_duplicate")
        if set(names) != set(manifest_city_names) or len(names) != len(manifest_city_names):
            issues.append("readme_city_list_mismatch")
    if len(manifest_city_names) != registered_cities:
        issues.append("manifest_city_count_mismatch")
    if production_minimum_cities != registered_cities:
        issues.append("production_minimum_city_count_mismatch")
    if guide_minimum is None:
        issues.append("deployment_guide_city_count_missing_or_ambiguous")
    elif guide_minimum != production_minimum_cities:
        issues.append("deployment_guide_city_count_mismatch")
    if registered_cities < 1:
        issues.append("empty_catalog_registry")
    return ReleaseConsistency(
        status="ready" if not issues else "inconsistent",
        registered_cities=registered_cities,
        documented_cities=documented,
        documented_city_names=names,
        production_minimum_cities=production_minimum_cities,
        deployment_guide_minimum_cities=guide_minimum,
        issues=tuple(issues),
    )


def collect_release_consistency(
    readme_path: str | Path, deployment_guide_path: str | Path = "docs/production-deployment.md"
) -> ReleaseConsistency:
    """Read public source documents only; never .env, secrets or user data."""
    manifests = list_city_manifests()
    return assess_release_consistency(
        Path(readme_path).read_text(encoding="utf-8"),
        deployment_guide=Path(deployment_guide_path).read_text(encoding="utf-8"),
        registered_cities=len(list_catalogs()),
        manifest_city_names=tuple(manifest.name for manifest in manifests),
        production_minimum_cities=MINIMUM_CITY_COUNT,
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--readme", default="README.md")
    parser.add_argument("--deployment-guide", default="docs/production-deployment.md")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    report = collect_release_consistency(args.readme, args.deployment_guide)
    print(json.dumps(asdict(report), ensure_ascii=False, sort_keys=True))
    if args.check and report.issues:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

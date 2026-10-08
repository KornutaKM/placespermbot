"""Read-only readiness checks before an operator-managed production rollout."""

from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.catalog import list_catalogs
from app.config import Settings, get_settings
from app.database import LATEST_SCHEMA_VERSION
from app.database_contract import validate_database_contract
from app.runtime_checks import validate_health

MINIMUM_CITY_COUNT = 32
FUTURE_CLOCK_TOLERANCE_SECONDS = 300


@dataclass(frozen=True, slots=True)
class DeploymentReadiness:
    status: str
    environment: str
    catalogs: int
    schema_version: int
    backup_age_minutes: int
    backup_size_bytes: int


def _validate_backup_readonly(backup: Path) -> None:
    try:
        with sqlite3.connect(f"file:{backup}?mode=ro", uri=True) as db:
            db.execute("PRAGMA query_only = ON")
            validate_database_contract(db, subject="Backup", check_integrity=True)
    except sqlite3.DatabaseError as exc:
        raise RuntimeError("Backup SQLite integrity check failed") from exc


async def collect_deployment_readiness(
    settings: Settings,
    backup_path: str | Path,
    *,
    max_age_hours: float = 24,
    min_cities: int = MINIMUM_CITY_COUNT,
) -> DeploymentReadiness:
    """Never mutate the database, backup, container state or environment."""
    if max_age_hours <= 0:
        raise ValueError("max_age_hours must be positive")
    if min_cities <= 0:
        raise ValueError("min_cities must be positive")
    if settings.environment != "production":
        raise RuntimeError("Preflight requires PLACES_ENVIRONMENT=production")

    db_path = Path(settings.database_path).resolve()
    backup = Path(backup_path).resolve()
    if backup == db_path:
        raise ValueError("Backup must not be the live database")
    if not backup.is_file():
        raise RuntimeError("Backup file does not exist")
    if not db_path.is_file():
        raise RuntimeError("Live database is not initialized")
    if len(list_catalogs()) < min_cities:
        raise RuntimeError("Registered city catalog count is below release minimum")

    await validate_health(settings)
    stat = backup.stat()
    if stat.st_size <= 0:
        raise RuntimeError("Backup is empty")
    age_seconds = datetime.now(UTC).timestamp() - stat.st_mtime
    if age_seconds < -FUTURE_CLOCK_TOLERANCE_SECONDS:
        raise RuntimeError("Backup timestamp is in the future")
    if age_seconds > max_age_hours * 3600:
        raise RuntimeError("Backup is too old for deployment")
    await asyncio.to_thread(_validate_backup_readonly, backup)

    return DeploymentReadiness(
        status="ready",
        environment=settings.environment,
        catalogs=len(list_catalogs()),
        schema_version=LATEST_SCHEMA_VERSION,
        backup_age_minutes=max(0, int(age_seconds // 60)),
        backup_size_bytes=stat.st_size,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup", required=True, help="Read-only snapshot to validate")
    parser.add_argument("--max-age-hours", type=float, default=24)
    parser.add_argument("--min-cities", type=int, default=MINIMUM_CITY_COUNT)
    args = parser.parse_args()
    result = asyncio.run(
        collect_deployment_readiness(
            get_settings(),
            args.backup,
            max_age_hours=args.max_age_hours,
            min_cities=args.min_cities,
        )
    )
    print(json.dumps(asdict(result), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

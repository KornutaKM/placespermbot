from __future__ import annotations

from pathlib import Path

import aiosqlite

from app.catalog import get_catalog
from app.config import Settings
from app.database import KNOWN_SCHEMA_VERSIONS, get_applied_migration_versions

EXPECTED_TABLES = frozenset(
    {
        "schema_migrations",
        "favorites",
        "user_interests",
        "user_city_preferences",
        "visited_places",
    }
)


def validate_static_runtime(settings: Settings) -> None:
    settings.require_bot_token()

    catalog = get_catalog(settings.city_slug)
    if not catalog.places:
        raise RuntimeError("Active city catalog is empty")


async def validate_health(settings: Settings) -> None:
    validate_static_runtime(settings)

    database_path = Path(settings.database_path)
    if not database_path.is_file():
        raise RuntimeError("Database is not initialized")

    async with aiosqlite.connect(database_path) as database:
        cursor = await database.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        )
        rows = await cursor.fetchall()
        await cursor.close()

    existing_tables = {str(row[0]) for row in rows}
    missing_tables = EXPECTED_TABLES - existing_tables
    if missing_tables:
        missing = ", ".join(sorted(missing_tables))
        raise RuntimeError(f"Database schema is incomplete: {missing}")

    applied_versions = set(
        await get_applied_migration_versions(database_path)
    )
    unknown_versions = applied_versions - KNOWN_SCHEMA_VERSIONS
    if unknown_versions:
        versions = ", ".join(str(version) for version in sorted(unknown_versions))
        raise RuntimeError(f"Database schema is newer than this app: {versions}")

    missing_versions = KNOWN_SCHEMA_VERSIONS - applied_versions
    if missing_versions:
        versions = ", ".join(str(version) for version in sorted(missing_versions))
        raise RuntimeError(f"Database migrations are incomplete: {versions}")

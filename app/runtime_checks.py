from __future__ import annotations

from pathlib import Path

import aiosqlite

from app.catalog import get_catalog
from app.config import Settings

EXPECTED_TABLES = frozenset({"favorites", "user_interests"})


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

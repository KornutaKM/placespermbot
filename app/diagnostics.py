from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from app.config import Settings, get_settings
from app.database import connect_database, get_applied_migration_versions
from app.runtime_checks import validate_health


async def collect_diagnostics(settings: Settings) -> dict[str, Any]:
    await validate_health(settings)
    database_path = Path(settings.database_path)
    versions = await get_applied_migration_versions(database_path)

    async with connect_database(database_path) as database:
        journal_cursor = await database.execute("PRAGMA journal_mode")
        journal_row = await journal_cursor.fetchone()
        await journal_cursor.close()

        integrity_cursor = await database.execute("PRAGMA quick_check")
        integrity_row = await integrity_cursor.fetchone()
        await integrity_cursor.close()

    return {
        "status": "healthy",
        "environment": settings.environment,
        "city_slug": settings.city_slug,
        "database": {
            "size_bytes": database_path.stat().st_size,
            "journal_mode": str(journal_row[0]) if journal_row else None,
            "integrity": str(integrity_row[0]) if integrity_row else None,
            "migration_versions": list(versions),
            "latest_migration": max(versions, default=0),
        },
    }


async def _main() -> None:
    diagnostics = await collect_diagnostics(get_settings())
    print(json.dumps(diagnostics, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(_main())

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from app.config import Settings, get_settings
from app.database import connect_database
from app.database_contract import validate_database_contract, validate_integrity_result
from app.release_identity import public_build_sha
from app.runtime_checks import validate_static_runtime


async def collect_diagnostics(settings: Settings) -> dict[str, Any]:
    validate_static_runtime(settings)
    database_path = Path(settings.database_path)
    if not database_path.is_file():
        raise RuntimeError("Database is not initialized")

    async with connect_database(database_path) as database:
        await database.execute("BEGIN")
        journal_cursor = await database.execute("PRAGMA journal_mode")
        journal_row = await journal_cursor.fetchone()
        await journal_cursor.close()

        integrity_cursor = await database.execute("PRAGMA quick_check")
        integrity_row = await integrity_cursor.fetchone()
        await integrity_cursor.close()
        validate_integrity_result(
            integrity_row,
            subject="Database",
            mode="quick",
        )

        migration_cursor = await database.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        )
        migration_rows = await migration_cursor.fetchall()
        await migration_cursor.close()
        await database.rollback()

    await asyncio.to_thread(_validate_contract, database_path)
    versions = tuple(int(row[0]) for row in migration_rows)

    return {
        "status": "healthy",
        "environment": settings.environment,
        "build_sha": public_build_sha(settings.build_sha),
        "city_slug": settings.city_slug,
        "database": {
            "size_bytes": database_path.stat().st_size,
            "journal_mode": str(journal_row[0]) if journal_row else None,
            "integrity": str(integrity_row[0]) if integrity_row else None,
            "migration_versions": list(versions),
            "latest_migration": max(versions, default=0),
        },
    }


def _validate_contract(database_path: Path) -> None:
    import sqlite3

    try:
        with sqlite3.connect(f"file:{database_path}?mode=ro", uri=True) as database:
            validate_database_contract(database, subject="Database")
    except sqlite3.DatabaseError as error:
        raise RuntimeError("Database is not a valid SQLite database") from error


async def _main() -> None:
    diagnostics = await collect_diagnostics(get_settings())
    print(json.dumps(diagnostics, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(_main())

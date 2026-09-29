from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import aiosqlite


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str
    statements: tuple[str, ...]


MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        version=1,
        name="create_favorites",
        statements=(
            """
            CREATE TABLE IF NOT EXISTS favorites (
                user_id INTEGER NOT NULL,
                city_slug TEXT NOT NULL,
                place_slug TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, city_slug, place_slug)
            )
            """,
        ),
    ),
    Migration(
        version=2,
        name="create_user_interests",
        statements=(
            """
            CREATE TABLE IF NOT EXISTS user_interests (
                user_id INTEGER NOT NULL,
                city_slug TEXT NOT NULL,
                interest TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, city_slug, interest)
            )
            """,
        ),
    ),
    Migration(
        version=3,
        name="create_user_city_preferences",
        statements=(
            """
            CREATE TABLE IF NOT EXISTS user_city_preferences (
                user_id INTEGER PRIMARY KEY,
                city_slug TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """,
        ),
    ),
)

KNOWN_SCHEMA_VERSIONS = frozenset(migration.version for migration in MIGRATIONS)
LATEST_SCHEMA_VERSION = max(KNOWN_SCHEMA_VERSIONS)


async def migrate_database(database_path: str | Path) -> int:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(path) as database:
        await database.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await database.commit()

        applied = await _applied_versions(database)
        unknown = applied - KNOWN_SCHEMA_VERSIONS
        if unknown:
            versions = ", ".join(str(version) for version in sorted(unknown))
            raise RuntimeError(f"Database schema is newer than this app: {versions}")

        for migration in MIGRATIONS:
            if migration.version in applied:
                continue

            try:
                await database.execute("BEGIN IMMEDIATE")
                for statement in migration.statements:
                    await database.execute(statement)
                await database.execute(
                    """
                    INSERT INTO schema_migrations (version, name)
                    VALUES (?, ?)
                    """,
                    (migration.version, migration.name),
                )
                await database.commit()
            except aiosqlite.Error:
                await database.rollback()
                raise

            applied.add(migration.version)

    return max(applied, default=0)


async def get_applied_migration_versions(
    database_path: str | Path,
) -> tuple[int, ...]:
    path = Path(database_path)
    if not path.is_file():
        return ()

    async with aiosqlite.connect(path) as database:
        cursor = await database.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'schema_migrations'
            """
        )
        migration_table = await cursor.fetchone()
        await cursor.close()

        if migration_table is None:
            return ()

        versions = await _applied_versions(database)

    return tuple(sorted(versions))


async def _applied_versions(database: aiosqlite.Connection) -> set[int]:
    cursor = await database.execute(
        """
        SELECT version
        FROM schema_migrations
        ORDER BY version ASC
        """
    )
    rows = await cursor.fetchall()
    await cursor.close()
    return {int(row[0]) for row in rows}

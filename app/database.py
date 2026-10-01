from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

import aiosqlite

SQLITE_BUSY_TIMEOUT_MS = 5_000


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
    Migration(
        version=4,
        name="create_visited_places",
        statements=(
            """
            CREATE TABLE IF NOT EXISTS visited_places (
                user_id INTEGER NOT NULL,
                city_slug TEXT NOT NULL,
                place_slug TEXT NOT NULL,
                visited_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, city_slug, place_slug)
            )
            """,
        ),
    ),
    Migration(
        version=5,
        name="create_saved_routes",
        statements=(
            """
            CREATE TABLE IF NOT EXISTS saved_routes (
                user_id INTEGER NOT NULL,
                city_slug TEXT NOT NULL,
                route_id TEXT NOT NULL,
                interest TEXT NOT NULL,
                budget_minutes INTEGER NOT NULL,
                place_slugs_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, city_slug, route_id)
            )
            """,
        ),
    ),
    Migration(
        version=6,
        name="create_dismissed_places",
        statements=(
            """
            CREATE TABLE IF NOT EXISTS dismissed_places (
                user_id INTEGER NOT NULL,
                city_slug TEXT NOT NULL,
                place_slug TEXT NOT NULL,
                dismissed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, city_slug, place_slug)
            )
            """,
        ),
    ),
    Migration(
        version=7,
        name="create_completed_routes",
        statements=(
            """
            CREATE TABLE IF NOT EXISTS completed_routes (
                user_id INTEGER NOT NULL,
                city_slug TEXT NOT NULL,
                route_id TEXT NOT NULL,
                completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, city_slug, route_id)
            )
            """,
        ),
    ),
    Migration(
        version=8,
        name="create_completed_route_snapshots",
        statements=(
            """
            CREATE TABLE IF NOT EXISTS completed_route_snapshots (
                user_id INTEGER NOT NULL,
                city_slug TEXT NOT NULL,
                route_id TEXT NOT NULL,
                interest TEXT NOT NULL,
                budget_minutes INTEGER NOT NULL,
                place_slugs_json TEXT NOT NULL,
                completed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, city_slug, route_id)
            )
            """,
        ),
    ),
    Migration(
        version=9,
        name="backfill_completed_route_snapshots",
        statements=(
            """
            INSERT OR IGNORE INTO completed_route_snapshots (
                user_id,
                city_slug,
                route_id,
                interest,
                budget_minutes,
                place_slugs_json,
                completed_at
            )
            SELECT
                completed.user_id,
                completed.city_slug,
                completed.route_id,
                saved.interest,
                saved.budget_minutes,
                saved.place_slugs_json,
                completed.completed_at
            FROM completed_routes AS completed
            INNER JOIN saved_routes AS saved
                ON saved.user_id = completed.user_id
                AND saved.city_slug = completed.city_slug
                AND saved.route_id = completed.route_id
            """,
        ),
    ),
)

KNOWN_SCHEMA_VERSIONS = frozenset(migration.version for migration in MIGRATIONS)
EXPECTED_MIGRATION_NAMES = {migration.version: migration.name for migration in MIGRATIONS}
LATEST_SCHEMA_VERSION = max(KNOWN_SCHEMA_VERSIONS)


def validate_migration_ledger(
    rows: list[tuple[int, str]] | tuple[tuple[int, str], ...],
    *,
    subject: str = "Database",
    require_complete: bool = False,
) -> set[int]:
    ledger = {int(version): str(name) for version, name in rows}
    versions = set(ledger)

    unknown = versions - KNOWN_SCHEMA_VERSIONS
    if unknown:
        rendered = ", ".join(str(version) for version in sorted(unknown))
        raise RuntimeError(f"{subject} schema is newer than this app: {rendered}")

    mismatched = {
        version: (EXPECTED_MIGRATION_NAMES[version], ledger[version])
        for version in versions
        if ledger[version] != EXPECTED_MIGRATION_NAMES[version]
    }
    if mismatched:
        rendered = ", ".join(
            f"{version} expected {expected!r}, found {actual!r}"
            for version, (expected, actual) in sorted(mismatched.items())
        )
        raise RuntimeError(f"{subject} migration metadata is inconsistent: {rendered}")

    if require_complete:
        missing = KNOWN_SCHEMA_VERSIONS - versions
        if missing:
            rendered = ", ".join(str(version) for version in sorted(missing))
            raise RuntimeError(f"{subject} migrations are incomplete: {rendered}")

    return versions


@asynccontextmanager
async def connect_database(
    database_path: str | Path,
) -> AsyncIterator[aiosqlite.Connection]:
    database = await aiosqlite.connect(
        database_path,
        timeout=SQLITE_BUSY_TIMEOUT_MS / 1_000,
    )
    try:
        await database.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MS}")
        await database.execute("PRAGMA foreign_keys = ON")
        yield database
    finally:
        await database.close()


async def migrate_database(database_path: str | Path) -> int:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    async with connect_database(path) as database:
        await database.execute("PRAGMA journal_mode = WAL")
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

        applied = validate_migration_ledger(
            await _migration_ledger(database),
            subject="Database",
        )

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

    async with connect_database(path) as database:
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


async def _migration_ledger(
    database: aiosqlite.Connection,
) -> list[tuple[int, str]]:
    cursor = await database.execute(
        """
        SELECT version, name
        FROM schema_migrations
        ORDER BY version ASC
        """
    )
    rows = await cursor.fetchall()
    await cursor.close()
    return [(int(row[0]), str(row[1])) for row in rows]


async def _applied_versions(database: aiosqlite.Connection) -> set[int]:
    return {version for version, _ in await _migration_ledger(database)}

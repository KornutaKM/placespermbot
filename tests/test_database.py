import asyncio
import sqlite3

import pytest

from app.database import (
    LATEST_SCHEMA_VERSION,
    SQLITE_BUSY_TIMEOUT_MS,
    connect_database,
    get_applied_migration_versions,
    migrate_database,
)


def table_names(database_path) -> set[str]:
    with sqlite3.connect(database_path) as database:
        rows = database.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            """
        ).fetchall()
    return {str(row[0]) for row in rows}


def test_fresh_database_reaches_latest_schema(tmp_path) -> None:
    async def scenario() -> None:
        database_path = tmp_path / "places.db"

        version = await migrate_database(database_path)

        assert version == LATEST_SCHEMA_VERSION
        assert await get_applied_migration_versions(database_path) == (1, 2, 3, 4, 5, 6, 7, 8, 9)
        assert {
            "schema_migrations",
            "favorites",
            "user_interests",
            "user_city_preferences",
            "visited_places",
            "saved_routes",
            "dismissed_places",
            "completed_routes",
            "completed_route_snapshots",
        } <= table_names(database_path)

    asyncio.run(scenario())


def test_legacy_rows_survive_migration(tmp_path) -> None:
    async def scenario() -> None:
        database_path = tmp_path / "legacy.db"
        with sqlite3.connect(database_path) as database:
            database.execute(
                """
                CREATE TABLE favorites (
                    user_id INTEGER NOT NULL,
                    city_slug TEXT NOT NULL,
                    place_slug TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, city_slug, place_slug)
                )
                """
            )
            database.execute(
                """
                CREATE TABLE user_interests (
                    user_id INTEGER NOT NULL,
                    city_slug TEXT NOT NULL,
                    interest TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, city_slug, interest)
                )
                """
            )
            database.execute(
                """
                INSERT INTO favorites (user_id, city_slug, place_slug)
                VALUES (42, 'saint-petersburg', 'hermitage')
                """
            )
            database.execute(
                """
                INSERT INTO user_interests (user_id, city_slug, interest)
                VALUES (42, 'saint-petersburg', 'museums')
                """
            )
            database.commit()

        await migrate_database(database_path)

        with sqlite3.connect(database_path) as database:
            favorite = database.execute(
                """
                SELECT user_id, city_slug, place_slug
                FROM favorites
                """
            ).fetchone()
            interest = database.execute(
                """
                SELECT user_id, city_slug, interest
                FROM user_interests
                """
            ).fetchone()

        assert favorite == (42, "saint-petersburg", "hermitage")
        assert interest == (42, "saint-petersburg", "museums")
        assert await get_applied_migration_versions(database_path) == (1, 2, 3, 4, 5, 6, 7, 8, 9)

    asyncio.run(scenario())


def test_migration_is_idempotent(tmp_path) -> None:
    async def scenario() -> None:
        database_path = tmp_path / "places.db"

        first = await migrate_database(database_path)
        second = await migrate_database(database_path)

        assert first == LATEST_SCHEMA_VERSION
        assert second == LATEST_SCHEMA_VERSION
        assert await get_applied_migration_versions(database_path) == (1, 2, 3, 4, 5, 6, 7, 8, 9)

        with sqlite3.connect(database_path) as database:
            count = database.execute(
                "SELECT COUNT(*) FROM schema_migrations"
            ).fetchone()

        assert count == (9,)

    asyncio.run(scenario())


def test_future_schema_version_fails_closed(tmp_path) -> None:
    async def scenario() -> None:
        database_path = tmp_path / "future.db"
        with sqlite3.connect(database_path) as database:
            database.execute(
                """
                CREATE TABLE schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            database.execute(
                """
                INSERT INTO schema_migrations (version, name)
                VALUES (99, 'future_schema')
                """
            )
            database.commit()

        with pytest.raises(RuntimeError, match="newer than this app"):
            await migrate_database(database_path)

    asyncio.run(scenario())


def test_migration_backfills_only_recoverable_completed_route_snapshots(
    tmp_path,
) -> None:
    async def scenario() -> None:
        database_path = tmp_path / "legacy-completions.db"
        await migrate_database(database_path)

        with sqlite3.connect(database_path) as database:
            database.execute(
                "DELETE FROM schema_migrations WHERE version = 9"
            )
            database.execute(
                "DELETE FROM completed_route_snapshots"
            )
            database.execute(
                """
                INSERT INTO saved_routes (
                    user_id,
                    city_slug,
                    route_id,
                    interest,
                    budget_minutes,
                    place_slugs_json
                )
                VALUES (42, 'saint-petersburg', 'recoverable', 'museums', 240,
                        '["hermitage","russian-museum"]')
                """
            )
            database.execute(
                """
                INSERT INTO completed_routes (
                    user_id,
                    city_slug,
                    route_id,
                    completed_at
                )
                VALUES (42, 'saint-petersburg', 'recoverable',
                        '2026-09-01 12:00:00')
                """
            )
            database.execute(
                """
                INSERT INTO completed_routes (
                    user_id,
                    city_slug,
                    route_id,
                    completed_at
                )
                VALUES (42, 'saint-petersburg', 'orphan',
                        '2026-09-02 12:00:00')
                """
            )
            database.commit()

        assert await migrate_database(database_path) == LATEST_SCHEMA_VERSION

        with sqlite3.connect(database_path) as database:
            rows = database.execute(
                """
                SELECT route_id, interest, budget_minutes, place_slugs_json,
                       completed_at
                FROM completed_route_snapshots
                ORDER BY route_id
                """
            ).fetchall()

        assert rows == [
            (
                "recoverable",
                "museums",
                240,
                '["hermitage","russian-museum"]',
                "2026-09-01 12:00:00",
            )
        ]

    asyncio.run(scenario())


def test_database_uses_wal_and_busy_timeout(tmp_path) -> None:
    async def scenario() -> None:
        database_path = tmp_path / "places.db"
        await migrate_database(database_path)

        async with connect_database(database_path) as database:
            journal = await database.execute("PRAGMA journal_mode")
            journal_row = await journal.fetchone()
            await journal.close()
            timeout = await database.execute("PRAGMA busy_timeout")
            timeout_row = await timeout.fetchone()
            await timeout.close()
            foreign_keys = await database.execute("PRAGMA foreign_keys")
            foreign_keys_row = await foreign_keys.fetchone()
            await foreign_keys.close()

        assert journal_row == ("wal",)
        assert timeout_row == (SQLITE_BUSY_TIMEOUT_MS,)
        assert foreign_keys_row == (1,)

    asyncio.run(scenario())


def test_concurrent_writers_wait_instead_of_failing_locked(tmp_path) -> None:
    async def scenario() -> None:
        database_path = tmp_path / "places.db"
        await migrate_database(database_path)

        first_context = connect_database(database_path)
        first = await first_context.__aenter__()
        try:
            await first.execute("BEGIN IMMEDIATE")
            await first.execute(
                """
                INSERT INTO favorites (user_id, city_slug, place_slug)
                VALUES (1, 'saint-petersburg', 'hermitage')
                """
            )

            async def delayed_release() -> None:
                await asyncio.sleep(0.1)
                await first.commit()

            async def waiting_writer() -> None:
                async with connect_database(database_path) as second:
                    await second.execute(
                        """
                        INSERT INTO favorites (user_id, city_slug, place_slug)
                        VALUES (2, 'saint-petersburg', 'russian-museum')
                        """
                    )
                    await second.commit()

            await asyncio.gather(delayed_release(), waiting_writer())
        finally:
            await first_context.__aexit__(None, None, None)

        with sqlite3.connect(database_path) as database:
            count = database.execute(
                "SELECT COUNT(*) FROM favorites"
            ).fetchone()
        assert count == (2,)

    asyncio.run(scenario())


def test_migration_rejects_known_version_with_wrong_name_before_applying_more(tmp_path) -> None:
    async def scenario() -> None:
        database_path = tmp_path / "tampered.db"
        await migrate_database(database_path)

        with sqlite3.connect(database_path) as database:
            database.execute(
                "UPDATE schema_migrations SET name = 'tampered' WHERE version = 5"
            )
            database.execute("DELETE FROM schema_migrations WHERE version = 9")
            database.commit()

        with pytest.raises(RuntimeError, match="migration metadata is inconsistent"):
            await migrate_database(database_path)

        with sqlite3.connect(database_path) as database:
            versions = database.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            ).fetchall()
        assert versions == [(1,), (2,), (3,), (4,), (5,), (6,), (7,), (8,)]

    asyncio.run(scenario())

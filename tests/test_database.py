import asyncio
import sqlite3

import pytest

from app.database import (
    LATEST_SCHEMA_VERSION,
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
        assert await get_applied_migration_versions(database_path) == (1, 2, 3, 4, 5, 6, 7)
        assert {
            "schema_migrations",
            "favorites",
            "user_interests",
            "user_city_preferences",
            "visited_places",
            "saved_routes",
            "dismissed_places",
            "completed_routes",
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
        assert await get_applied_migration_versions(database_path) == (1, 2, 3, 4, 5, 6, 7)

    asyncio.run(scenario())


def test_migration_is_idempotent(tmp_path) -> None:
    async def scenario() -> None:
        database_path = tmp_path / "places.db"

        first = await migrate_database(database_path)
        second = await migrate_database(database_path)

        assert first == LATEST_SCHEMA_VERSION
        assert second == LATEST_SCHEMA_VERSION
        assert await get_applied_migration_versions(database_path) == (1, 2, 3, 4, 5, 6, 7)

        with sqlite3.connect(database_path) as database:
            count = database.execute(
                "SELECT COUNT(*) FROM schema_migrations"
            ).fetchone()

        assert count == (7,)

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

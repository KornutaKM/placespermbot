import asyncio
import sqlite3

import pytest

from app.config import Settings
from app.database import migrate_database
from app.runtime_checks import validate_health, validate_static_runtime


def settings(tmp_path, **overrides) -> Settings:
    values = {
        "bot_token": "123456789:test-token",
        "city_slug": "saint-petersburg",
        "database_path": str(tmp_path / "places.db"),
        "environment": "test",
    }
    values.update(overrides)
    return Settings(**values)


def test_static_runtime_accepts_valid_config(tmp_path) -> None:
    validate_static_runtime(settings(tmp_path))


def test_static_runtime_rejects_missing_token(tmp_path) -> None:
    with pytest.raises(RuntimeError, match="PLACES_BOT_TOKEN"):
        validate_static_runtime(settings(tmp_path, bot_token="replace-me"))


def test_static_runtime_rejects_unknown_city(tmp_path) -> None:
    with pytest.raises(RuntimeError, match="Unsupported city"):
        validate_static_runtime(settings(tmp_path, city_slug="unknown-city"))


def test_health_accepts_initialized_database(tmp_path) -> None:
    async def scenario() -> None:
        config = settings(tmp_path)
        await migrate_database(config.database_path)

        await validate_health(config)

    asyncio.run(scenario())


def test_health_rejects_missing_database(tmp_path) -> None:
    async def scenario() -> None:
        with pytest.raises(RuntimeError, match="Database is not initialized"):
            await validate_health(settings(tmp_path))

    asyncio.run(scenario())


def test_health_rejects_incomplete_schema(tmp_path) -> None:
    async def scenario() -> None:
        config = settings(tmp_path)
        with sqlite3.connect(config.database_path) as database:
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
                INSERT INTO schema_migrations (version, name)
                VALUES (1, 'create_favorites')
                """
            )
            database.commit()

        with pytest.raises(RuntimeError, match="user_interests"):
            await validate_health(config)

    asyncio.run(scenario())


def test_health_rejects_missing_completed_route_snapshot_table(tmp_path) -> None:
    async def scenario() -> None:
        config = settings(tmp_path)
        await migrate_database(config.database_path)

        with sqlite3.connect(config.database_path) as database:
            database.execute("DROP TABLE completed_route_snapshots")
            database.commit()

        with pytest.raises(
            RuntimeError,
            match="completed_route_snapshots",
        ):
            await validate_health(config)

    asyncio.run(scenario())


def test_health_rejects_table_with_missing_required_columns(tmp_path) -> None:
    async def scenario() -> None:
        config = settings(tmp_path)
        await migrate_database(config.database_path)

        with sqlite3.connect(config.database_path) as database:
            database.execute("DROP TABLE saved_routes")
            database.execute(
                """
                CREATE TABLE saved_routes (
                    user_id INTEGER NOT NULL,
                    city_slug TEXT NOT NULL,
                    route_id TEXT NOT NULL,
                    PRIMARY KEY (user_id, city_slug, route_id)
                )
                """
            )
            database.commit()

        with pytest.raises(RuntimeError, match=r"saved_routes.*budget_minutes"):
            await validate_health(config)

    asyncio.run(scenario())

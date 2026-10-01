import asyncio
import sqlite3
from unittest.mock import patch

import pytest

from app.config import Settings
from app.database import migrate_database
from app.runtime_checks import validate_health, validate_static_runtime
from app.storage import SavedRoutesRepository


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


def test_health_uses_quick_integrity_gate(tmp_path) -> None:
    async def scenario() -> None:
        config = settings(tmp_path)
        await migrate_database(config.database_path)

        with patch("app.runtime_checks.validate_database_integrity") as validate_integrity:
            await validate_health(config)

        validate_integrity.assert_called_once()
        assert validate_integrity.call_args.kwargs == {
            "subject": "Database",
            "mode": "quick",
        }

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


def test_health_rejects_tampered_migration_name(tmp_path) -> None:
    async def scenario() -> None:
        config = settings(tmp_path)
        await migrate_database(config.database_path)
        with sqlite3.connect(config.database_path) as database:
            database.execute(
                "UPDATE schema_migrations SET name = 'tampered' WHERE version = 4"
            )
            database.commit()

        with pytest.raises(RuntimeError, match="migration metadata is inconsistent"):
            await validate_health(config)

    asyncio.run(scenario())


def test_health_rejects_tampered_saved_route_snapshot(tmp_path) -> None:
    async def scenario() -> None:
        config = settings(tmp_path)
        await migrate_database(config.database_path)
        saved_routes = SavedRoutesRepository(config.database_path)
        route = await saved_routes.save(
            21,
            "saint-petersburg",
            "classic",
            120,
            ("hermitage", "russian-museum"),
        )

        with sqlite3.connect(config.database_path) as database:
            database.execute(
                """
                UPDATE saved_routes
                SET place_slugs_json = ?
                WHERE route_id = ?
                """,
                ('["hermitage","summer-garden"]', route.route_id),
            )
            database.commit()

        with pytest.raises(RuntimeError, match="id does not match"):
            await validate_health(config)

    asyncio.run(scenario())


def test_health_rejects_completed_snapshot_without_marker(tmp_path) -> None:
    async def scenario() -> None:
        config = settings(tmp_path)
        await migrate_database(config.database_path)
        saved_routes = SavedRoutesRepository(config.database_path)
        route = await saved_routes.save(
            22,
            "saint-petersburg",
            "classic",
            120,
            ("hermitage", "russian-museum"),
        )

        with sqlite3.connect(config.database_path) as database:
            database.execute(
                """
                INSERT INTO completed_route_snapshots (
                    user_id, city_slug, route_id, interest,
                    budget_minutes, place_slugs_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    22,
                    route.city_slug,
                    route.route_id,
                    route.interest,
                    route.budget_minutes,
                    '["hermitage","russian-museum"]',
                ),
            )
            database.commit()

        with pytest.raises(RuntimeError, match="snapshot without its marker"):
            await validate_health(config)

    asyncio.run(scenario())


def test_health_allows_legacy_completion_marker_without_snapshot(tmp_path) -> None:
    async def scenario() -> None:
        config = settings(tmp_path)
        await migrate_database(config.database_path)

        with sqlite3.connect(config.database_path) as database:
            database.execute(
                """
                INSERT INTO completed_routes (user_id, city_slug, route_id)
                VALUES (?, ?, ?)
                """,
                (23, "saint-petersburg", "legacy-unrecoverable"),
            )
            database.commit()

        await validate_health(config)

    asyncio.run(scenario())


def test_health_rejects_mismatched_completion_timestamps(tmp_path) -> None:
    async def scenario() -> None:
        config = settings(tmp_path)
        await migrate_database(config.database_path)
        saved_routes = SavedRoutesRepository(config.database_path)
        route = await saved_routes.save(
            24,
            "saint-petersburg",
            "classic",
            120,
            ("hermitage", "russian-museum"),
        )

        with sqlite3.connect(config.database_path) as database:
            database.execute(
                """
                INSERT INTO completed_routes (
                    user_id, city_slug, route_id, completed_at
                )
                VALUES (?, ?, ?, ?)
                """,
                (24, route.city_slug, route.route_id, "2026-01-01 10:00:00"),
            )
            database.execute(
                """
                INSERT INTO completed_route_snapshots (
                    user_id, city_slug, route_id, interest,
                    budget_minutes, place_slugs_json, completed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    24,
                    route.city_slug,
                    route.route_id,
                    route.interest,
                    route.budget_minutes,
                    '["hermitage","russian-museum"]',
                    "2026-01-01 10:00:01",
                ),
            )
            database.commit()

        with pytest.raises(RuntimeError, match="inconsistent completed route timestamps"):
            await validate_health(config)

    asyncio.run(scenario())


def test_health_rejects_table_with_wrong_primary_key(tmp_path) -> None:
    async def scenario() -> None:
        config = settings(tmp_path)
        await migrate_database(config.database_path)

        with sqlite3.connect(config.database_path) as database:
            database.execute("ALTER TABLE favorites RENAME TO favorites_old")
            database.execute(
                """
                CREATE TABLE favorites (
                    user_id INTEGER NOT NULL,
                    city_slug TEXT NOT NULL,
                    place_slug TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, city_slug)
                )
                """
            )
            database.execute(
                """
                INSERT INTO favorites
                SELECT user_id, city_slug, place_slug, created_at
                FROM favorites_old
                """
            )
            database.execute("DROP TABLE favorites_old")
            database.commit()

        with pytest.raises(RuntimeError, match="invalid primary key"):
            await validate_health(config)

    asyncio.run(scenario())

@pytest.mark.parametrize(
    "place_slug_definition",
    (
        "INTEGER NOT NULL",
        "TEXT",
        "TEXT NOT NULL DEFAULT 'unexpected'",
    ),
)
def test_health_rejects_invalid_column_definition(
    tmp_path,
    place_slug_definition: str,
) -> None:
    async def scenario() -> None:
        config = settings(tmp_path)
        await migrate_database(config.database_path)

        with sqlite3.connect(config.database_path) as database:
            database.execute("ALTER TABLE favorites RENAME TO favorites_old")
            database.execute(
                f"""
                CREATE TABLE favorites (
                    user_id INTEGER NOT NULL,
                    city_slug TEXT NOT NULL,
                    place_slug {place_slug_definition},
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, city_slug, place_slug)
                )
                """
            )
            database.execute("DROP TABLE favorites_old")
            database.commit()

        with pytest.raises(RuntimeError, match="column place_slug has an invalid definition"):
            await validate_health(config)

    asyncio.run(scenario())


from __future__ import annotations

from pathlib import Path

from app.catalog import get_catalog
from app.config import Settings
from app.database import (
    connect_database,
    validate_migration_ledger,
)
from app.storage import validate_persisted_route_row

EXPECTED_TABLES = frozenset(
    {
        "schema_migrations",
        "favorites",
        "user_interests",
        "user_city_preferences",
        "visited_places",
        "saved_routes",
        "dismissed_places",
        "completed_routes",
        "completed_route_snapshots",
    }
)

EXPECTED_COLUMNS: dict[str, frozenset[str]] = {
    "schema_migrations": frozenset({"version", "name", "applied_at"}),
    "favorites": frozenset({"user_id", "city_slug", "place_slug", "created_at"}),
    "user_interests": frozenset(
        {"user_id", "city_slug", "interest", "created_at"}
    ),
    "user_city_preferences": frozenset(
        {"user_id", "city_slug", "updated_at"}
    ),
    "visited_places": frozenset(
        {"user_id", "city_slug", "place_slug", "visited_at"}
    ),
    "saved_routes": frozenset(
        {
            "user_id",
            "city_slug",
            "route_id",
            "interest",
            "budget_minutes",
            "place_slugs_json",
            "created_at",
        }
    ),
    "dismissed_places": frozenset(
        {"user_id", "city_slug", "place_slug", "dismissed_at"}
    ),
    "completed_routes": frozenset(
        {"user_id", "city_slug", "route_id", "completed_at"}
    ),
    "completed_route_snapshots": frozenset(
        {
            "user_id",
            "city_slug",
            "route_id",
            "interest",
            "budget_minutes",
            "place_slugs_json",
            "completed_at",
        }
    ),
}


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

    async with connect_database(database_path) as database:
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

    async with connect_database(database_path) as database:
        for table_name, expected_columns in EXPECTED_COLUMNS.items():
            cursor = await database.execute(f"PRAGMA table_info({table_name})")
            column_rows = await cursor.fetchall()
            await cursor.close()
            existing_columns = {str(row[1]) for row in column_rows}
            missing_columns = expected_columns - existing_columns
            if missing_columns:
                missing = ", ".join(sorted(missing_columns))
                raise RuntimeError(
                    "Database table "
                    f"{table_name} is incomplete; missing columns: {missing}"
                )

    async with connect_database(database_path) as database:
        cursor = await database.execute(
            "SELECT version, name FROM schema_migrations ORDER BY version"
        )
        migration_rows = await cursor.fetchall()
        await cursor.close()

    validate_migration_ledger(
        [(int(row[0]), str(row[1])) for row in migration_rows],
        subject="Database",
        require_complete=True,
    )

    async with connect_database(database_path) as database:
        for table_name, kind in (
            ("saved_routes", "saved route"),
            ("completed_route_snapshots", "completed route"),
        ):
            cursor = await database.execute(
                f"""
                SELECT route_id, city_slug, interest, budget_minutes,
                       place_slugs_json, NULL
                FROM {table_name}
                """
            )
            route_rows = await cursor.fetchall()
            await cursor.close()
            for row in route_rows:
                validate_persisted_route_row(tuple(row), kind=kind)

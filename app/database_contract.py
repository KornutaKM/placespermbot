from __future__ import annotations

import sqlite3

from app.database import validate_migration_ledger
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
    "user_interests": frozenset({"user_id", "city_slug", "interest", "created_at"}),
    "user_city_preferences": frozenset({"user_id", "city_slug", "updated_at"}),
    "visited_places": frozenset({"user_id", "city_slug", "place_slug", "visited_at"}),
    "saved_routes": frozenset(
        {
            "user_id", "city_slug", "route_id", "interest",
            "budget_minutes", "place_slugs_json", "created_at",
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
            "user_id", "city_slug", "route_id", "interest",
            "budget_minutes", "place_slugs_json", "completed_at",
        }
    ),
}


def validate_database_contract(
    database: sqlite3.Connection,
    *,
    subject: str,
    check_integrity: bool = False,
) -> None:
    if check_integrity:
        integrity = database.execute("PRAGMA integrity_check").fetchone()
        if integrity != ("ok",):
            raise RuntimeError(f"{subject} database failed integrity check")

    existing_tables = {
        str(row[0])
        for row in database.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    missing_tables = EXPECTED_TABLES - existing_tables
    if missing_tables:
        missing = ", ".join(sorted(missing_tables))
        raise RuntimeError(f"{subject} schema is incomplete: {missing}")

    for table_name, expected_columns in EXPECTED_COLUMNS.items():
        existing_columns = {
            str(row[1])
            for row in database.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        missing_columns = expected_columns - existing_columns
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise RuntimeError(
                f"{subject} table {table_name} is incomplete; missing columns: {missing}"
            )

    migration_rows = database.execute(
        "SELECT version, name FROM schema_migrations ORDER BY version"
    ).fetchall()
    validate_migration_ledger(
        [(int(row[0]), str(row[1])) for row in migration_rows],
        subject=subject,
        require_complete=True,
    )

    for table_name, kind in (
        ("saved_routes", "saved route"),
        ("completed_route_snapshots", "completed route"),
    ):
        route_rows = database.execute(
            f"""
            SELECT route_id, city_slug, interest, budget_minutes,
                   place_slugs_json, NULL
            FROM {table_name}
            """
        ).fetchall()
        for route_row in route_rows:
            validate_persisted_route_row(tuple(route_row), kind=kind)

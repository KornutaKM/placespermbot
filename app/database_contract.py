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


EXPECTED_PRIMARY_KEYS: dict[str, tuple[str, ...]] = {
    "schema_migrations": ("version",),
    "favorites": ("user_id", "city_slug", "place_slug"),
    "user_interests": ("user_id", "city_slug", "interest"),
    "user_city_preferences": ("user_id",),
    "visited_places": ("user_id", "city_slug", "place_slug"),
    "saved_routes": ("user_id", "city_slug", "route_id"),
    "dismissed_places": ("user_id", "city_slug", "place_slug"),
    "completed_routes": ("user_id", "city_slug", "route_id"),
    "completed_route_snapshots": ("user_id", "city_slug", "route_id"),
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
        table_info = database.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
        existing_columns = {str(row[1]) for row in table_info}
        missing_columns = expected_columns - existing_columns
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise RuntimeError(
                f"{subject} table {table_name} is incomplete; missing columns: {missing}"
            )

        actual_primary_key = tuple(
            str(row[1])
            for row in sorted(table_info, key=lambda row: int(row[5]))
            if int(row[5]) > 0
        )
        expected_primary_key = EXPECTED_PRIMARY_KEYS[table_name]
        if actual_primary_key != expected_primary_key:
            raise RuntimeError(
                f"{subject} table {table_name} has an invalid primary key"
            )

    migration_rows = database.execute(
        "SELECT version, name FROM schema_migrations ORDER BY version"
    ).fetchall()
    validate_migration_ledger(
        [(int(row[0]), str(row[1])) for row in migration_rows],
        subject=subject,
        require_complete=True,
    )

    orphan_snapshot = database.execute(
        """
        SELECT snapshot.user_id, snapshot.city_slug, snapshot.route_id
        FROM completed_route_snapshots AS snapshot
        LEFT JOIN completed_routes AS completed
            ON completed.user_id = snapshot.user_id
            AND completed.city_slug = snapshot.city_slug
            AND completed.route_id = snapshot.route_id
        WHERE completed.route_id IS NULL
        LIMIT 1
        """
    ).fetchone()
    if orphan_snapshot is not None:
        raise RuntimeError(
            f"{subject} contains a completed route snapshot without its marker"
        )

    timestamp_mismatch = database.execute(
        """
        SELECT 1
        FROM completed_route_snapshots AS snapshot
        INNER JOIN completed_routes AS completed
            ON completed.user_id = snapshot.user_id
            AND completed.city_slug = snapshot.city_slug
            AND completed.route_id = snapshot.route_id
        WHERE snapshot.completed_at != completed.completed_at
        LIMIT 1
        """
    ).fetchone()
    if timestamp_mismatch is not None:
        raise RuntimeError(
            f"{subject} contains inconsistent completed route timestamps"
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

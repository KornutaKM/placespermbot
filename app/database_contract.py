from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Literal

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


@dataclass(frozen=True, slots=True)
class ColumnContract:
    declared_type: str
    not_null: bool
    default_value: str | None = None


EXPECTED_COLUMN_CONTRACTS: dict[str, dict[str, ColumnContract]] = {
    "schema_migrations": {
        "version": ColumnContract("INTEGER", False),
        "name": ColumnContract("TEXT", True),
        "applied_at": ColumnContract("TEXT", True, "CURRENT_TIMESTAMP"),
    },
    "favorites": {
        "user_id": ColumnContract("INTEGER", True),
        "city_slug": ColumnContract("TEXT", True),
        "place_slug": ColumnContract("TEXT", True),
        "created_at": ColumnContract("TEXT", True, "CURRENT_TIMESTAMP"),
    },
    "user_interests": {
        "user_id": ColumnContract("INTEGER", True),
        "city_slug": ColumnContract("TEXT", True),
        "interest": ColumnContract("TEXT", True),
        "created_at": ColumnContract("TEXT", True, "CURRENT_TIMESTAMP"),
    },
    "user_city_preferences": {
        "user_id": ColumnContract("INTEGER", False),
        "city_slug": ColumnContract("TEXT", True),
        "updated_at": ColumnContract("TEXT", True, "CURRENT_TIMESTAMP"),
    },
    "visited_places": {
        "user_id": ColumnContract("INTEGER", True),
        "city_slug": ColumnContract("TEXT", True),
        "place_slug": ColumnContract("TEXT", True),
        "visited_at": ColumnContract("TEXT", True, "CURRENT_TIMESTAMP"),
    },
    "saved_routes": {
        "user_id": ColumnContract("INTEGER", True),
        "city_slug": ColumnContract("TEXT", True),
        "route_id": ColumnContract("TEXT", True),
        "interest": ColumnContract("TEXT", True),
        "budget_minutes": ColumnContract("INTEGER", True),
        "place_slugs_json": ColumnContract("TEXT", True),
        "created_at": ColumnContract("TEXT", True, "CURRENT_TIMESTAMP"),
    },
    "dismissed_places": {
        "user_id": ColumnContract("INTEGER", True),
        "city_slug": ColumnContract("TEXT", True),
        "place_slug": ColumnContract("TEXT", True),
        "dismissed_at": ColumnContract("TEXT", True, "CURRENT_TIMESTAMP"),
    },
    "completed_routes": {
        "user_id": ColumnContract("INTEGER", True),
        "city_slug": ColumnContract("TEXT", True),
        "route_id": ColumnContract("TEXT", True),
        "completed_at": ColumnContract("TEXT", True, "CURRENT_TIMESTAMP"),
    },
    "completed_route_snapshots": {
        "user_id": ColumnContract("INTEGER", True),
        "city_slug": ColumnContract("TEXT", True),
        "route_id": ColumnContract("TEXT", True),
        "interest": ColumnContract("TEXT", True),
        "budget_minutes": ColumnContract("INTEGER", True),
        "place_slugs_json": ColumnContract("TEXT", True),
        "completed_at": ColumnContract("TEXT", True, "CURRENT_TIMESTAMP"),
    },
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


IntegrityCheckMode = Literal["quick", "full"]


def validate_integrity_result(
    result: tuple[object, ...] | None,
    *,
    subject: str,
    mode: IntegrityCheckMode,
) -> None:
    if result == ("ok",):
        return

    check_name = "quick integrity check" if mode == "quick" else "integrity check"
    raise RuntimeError(f"{subject} database failed {check_name}")


def validate_database_integrity(
    database: sqlite3.Connection,
    *,
    subject: str,
    mode: IntegrityCheckMode,
) -> None:
    pragma = "quick_check" if mode == "quick" else "integrity_check"
    result = database.execute(f"PRAGMA {pragma}").fetchone()
    validate_integrity_result(result, subject=subject, mode=mode)


def validate_database_contract(
    database: sqlite3.Connection,
    *,
    subject: str,
    check_integrity: bool = False,
) -> None:
    if check_integrity:
        validate_database_integrity(database, subject=subject, mode="full")

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

    unexpected_tables = {
        table_name
        for table_name in existing_tables - EXPECTED_TABLES
        if not table_name.startswith("sqlite_")
    }
    if unexpected_tables:
        unexpected = ", ".join(sorted(unexpected_tables))
        raise RuntimeError(f"{subject} schema has unexpected tables: {unexpected}")

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

        unexpected_columns = existing_columns - expected_columns
        if unexpected_columns:
            unexpected = ", ".join(sorted(unexpected_columns))
            raise RuntimeError(
                f"{subject} table {table_name} has unexpected columns: {unexpected}"
            )

        column_rows = {str(row[1]): row for row in table_info}
        for column_name, expected in EXPECTED_COLUMN_CONTRACTS[table_name].items():
            column = column_rows[column_name]
            actual_type = str(column[2]).upper()
            actual_not_null = bool(column[3])
            actual_default = None if column[4] is None else str(column[4]).strip()
            if (
                actual_type != expected.declared_type
                or actual_not_null != expected.not_null
                or actual_default != expected.default_value
            ):
                raise RuntimeError(
                    f"{subject} table {table_name} column {column_name} "
                    "has an invalid definition"
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

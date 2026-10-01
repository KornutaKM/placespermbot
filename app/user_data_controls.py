from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import aiosqlite

_DATA_TABLES = (
    ("favorites", "favorites"),
    ("user_interests", "interests"),
    ("visited_places", "visited"),
    ("saved_routes", "saved_routes"),
    ("dismissed_places", "dismissed"),
    ("completed_routes", "completed_routes"),
    ("completed_route_snapshots", "completed_route_snapshots"),
)


@dataclass(frozen=True, slots=True)
class DeletionResult:
    favorites: int
    interests: int
    visited: int
    saved_routes: int
    dismissed: int
    completed_routes: int
    completed_route_snapshots: int

    @property
    def total(self) -> int:
        return (
            self.favorites
            + self.interests
            + self.visited
            + self.saved_routes
            + self.dismissed
            + self.completed_routes
            + self.completed_route_snapshots
        )


class UserDataControlsRepository:
    def __init__(self, database_path: str) -> None:
        self.database_path = Path(database_path)

    async def delete_city_data(
        self,
        user_id: int,
        city_slug: str,
    ) -> DeletionResult:
        counts: dict[str, int] = {}

        async with aiosqlite.connect(self.database_path) as database:
            try:
                await database.execute("BEGIN IMMEDIATE")
                for table_name, result_key in _DATA_TABLES:
                    cursor = await database.execute(
                        f"""
                        DELETE FROM {table_name}
                        WHERE user_id = ? AND city_slug = ?
                        """,
                        (user_id, city_slug),
                    )
                    counts[result_key] = max(cursor.rowcount, 0)
                    await cursor.close()
                await database.commit()
            except aiosqlite.Error:
                await database.rollback()
                raise

        return DeletionResult(
            favorites=counts["favorites"],
            interests=counts["interests"],
            visited=counts["visited"],
            saved_routes=counts["saved_routes"],
            dismissed=counts["dismissed"],
            completed_routes=counts["completed_routes"],
            completed_route_snapshots=counts["completed_route_snapshots"],
        )


def bound_city_slug(
    callback_data: str,
    *,
    prefix: str,
    current_city_slug: str,
) -> str:
    if not callback_data.startswith(prefix):
        raise ValueError("invalid data-control callback")

    requested_slug = callback_data.removeprefix(prefix).strip()
    if not requested_slug:
        raise ValueError("missing data-control city")

    if requested_slug != current_city_slug:
        raise ValueError("data-control city no longer active")

    return requested_slug

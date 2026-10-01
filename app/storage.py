import json
from dataclasses import dataclass
from pathlib import Path

import aiosqlite

from app.database import connect_database, migrate_database
from app.saved_routes import SavedRoute, route_id_for


def validate_persisted_route_row(
    row: tuple[object, ...],
    *,
    kind: str,
) -> None:
    route_id = str(row[0])
    city_slug = str(row[1])
    interest = str(row[2])
    budget_minutes = int(row[3])
    place_slugs = _decode_route_place_slugs(row[4], kind=kind)
    try:
        _validate_route_values(
            city_slug=city_slug,
            interest=interest,
            budget_minutes=budget_minutes,
            place_slugs=place_slugs,
        )
    except ValueError as exc:
        raise RuntimeError(f"{kind} contains invalid metadata") from exc

    expected_route_id = route_id_for(
        city_slug,
        interest,
        budget_minutes,
        place_slugs,
    )
    if route_id != expected_route_id:
        raise RuntimeError(f"{kind} id does not match persisted snapshot")


class FavoritesRepository:
    def __init__(self, database_path: str) -> None:
        self.database_path = Path(database_path)

    async def initialize(self) -> None:
        await migrate_database(self.database_path)

    async def add(self, user_id: int, city_slug: str, place_slug: str) -> None:
        async with connect_database(self.database_path) as database:
            await database.execute(
                """
                INSERT OR IGNORE INTO favorites (user_id, city_slug, place_slug)
                VALUES (?, ?, ?)
                """,
                (user_id, city_slug, place_slug),
            )
            await database.commit()

    async def remove(self, user_id: int, city_slug: str, place_slug: str) -> None:
        async with connect_database(self.database_path) as database:
            await database.execute(
                """
                DELETE FROM favorites
                WHERE user_id = ? AND city_slug = ? AND place_slug = ?
                """,
                (user_id, city_slug, place_slug),
            )
            await database.commit()

    async def contains(self, user_id: int, city_slug: str, place_slug: str) -> bool:
        async with connect_database(self.database_path) as database:
            cursor = await database.execute(
                """
                SELECT 1
                FROM favorites
                WHERE user_id = ? AND city_slug = ? AND place_slug = ?
                LIMIT 1
                """,
                (user_id, city_slug, place_slug),
            )
            row = await cursor.fetchone()
            await cursor.close()
            return row is not None

    async def list_place_slugs(self, user_id: int, city_slug: str) -> tuple[str, ...]:
        async with connect_database(self.database_path) as database:
            cursor = await database.execute(
                """
                SELECT place_slug
                FROM favorites
                WHERE user_id = ? AND city_slug = ?
                ORDER BY created_at DESC, place_slug ASC
                """,
                (user_id, city_slug),
            )
            rows = await cursor.fetchall()
            await cursor.close()
            return tuple(str(row[0]) for row in rows)



class InterestsRepository:
    def __init__(self, database_path: str) -> None:
        self.database_path = Path(database_path)

    async def initialize(self) -> None:
        await migrate_database(self.database_path)

    async def add(self, user_id: int, city_slug: str, interest: str) -> None:
        async with connect_database(self.database_path) as database:
            await database.execute(
                """
                INSERT OR IGNORE INTO user_interests (user_id, city_slug, interest)
                VALUES (?, ?, ?)
                """,
                (user_id, city_slug, interest),
            )
            await database.commit()

    async def remove(self, user_id: int, city_slug: str, interest: str) -> None:
        async with connect_database(self.database_path) as database:
            await database.execute(
                """
                DELETE FROM user_interests
                WHERE user_id = ? AND city_slug = ? AND interest = ?
                """,
                (user_id, city_slug, interest),
            )
            await database.commit()

    async def list_interests(self, user_id: int, city_slug: str) -> tuple[str, ...]:
        async with connect_database(self.database_path) as database:
            cursor = await database.execute(
                """
                SELECT interest
                FROM user_interests
                WHERE user_id = ? AND city_slug = ?
                ORDER BY interest ASC
                """,
                (user_id, city_slug),
            )
            rows = await cursor.fetchall()
            await cursor.close()
            return tuple(str(row[0]) for row in rows)



class UserCityRepository:
    def __init__(self, database_path: str) -> None:
        self.database_path = Path(database_path)

    async def initialize(self) -> None:
        await migrate_database(self.database_path)

    async def get_city_slug(self, user_id: int) -> str | None:
        async with connect_database(self.database_path) as database:
            cursor = await database.execute(
                """
                SELECT city_slug
                FROM user_city_preferences
                WHERE user_id = ?
                LIMIT 1
                """,
                (user_id,),
            )
            row = await cursor.fetchone()
            await cursor.close()

        if row is None:
            return None
        return str(row[0])

    async def set_city_slug(self, user_id: int, city_slug: str) -> None:
        async with connect_database(self.database_path) as database:
            await database.execute(
                """
                INSERT INTO user_city_preferences (user_id, city_slug)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    city_slug = excluded.city_slug,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, city_slug),
            )
            await database.commit()



class VisitedRepository:
    def __init__(self, database_path: str) -> None:
        self.database_path = Path(database_path)

    async def initialize(self) -> None:
        await migrate_database(self.database_path)

    async def add(self, user_id: int, city_slug: str, place_slug: str) -> None:
        async with connect_database(self.database_path) as database:
            await database.execute(
                """
                INSERT OR IGNORE INTO visited_places (
                    user_id,
                    city_slug,
                    place_slug
                )
                VALUES (?, ?, ?)
                """,
                (user_id, city_slug, place_slug),
            )
            await database.commit()

    async def remove(self, user_id: int, city_slug: str, place_slug: str) -> None:
        async with connect_database(self.database_path) as database:
            await database.execute(
                """
                DELETE FROM visited_places
                WHERE user_id = ? AND city_slug = ? AND place_slug = ?
                """,
                (user_id, city_slug, place_slug),
            )
            await database.commit()

    async def contains(self, user_id: int, city_slug: str, place_slug: str) -> bool:
        async with connect_database(self.database_path) as database:
            cursor = await database.execute(
                """
                SELECT 1
                FROM visited_places
                WHERE user_id = ? AND city_slug = ? AND place_slug = ?
                LIMIT 1
                """,
                (user_id, city_slug, place_slug),
            )
            row = await cursor.fetchone()
            await cursor.close()
            return row is not None

    async def list_place_slugs(self, user_id: int, city_slug: str) -> tuple[str, ...]:
        async with connect_database(self.database_path) as database:
            cursor = await database.execute(
                """
                SELECT place_slug
                FROM visited_places
                WHERE user_id = ? AND city_slug = ?
                ORDER BY visited_at DESC, place_slug ASC
                """,
                (user_id, city_slug),
            )
            rows = await cursor.fetchall()
            await cursor.close()
            return tuple(str(row[0]) for row in rows)



class SavedRoutesRepository:
    def __init__(self, database_path: str) -> None:
        self.database_path = Path(database_path)

    async def initialize(self) -> None:
        await migrate_database(self.database_path)

    async def save(
        self,
        user_id: int,
        city_slug: str,
        interest: str,
        budget_minutes: int,
        place_slugs: tuple[str, ...],
    ) -> SavedRoute:
        _validate_route_values(
            city_slug=city_slug,
            interest=interest,
            budget_minutes=budget_minutes,
            place_slugs=place_slugs,
        )

        route_id = route_id_for(
            city_slug,
            interest,
            budget_minutes,
            place_slugs,
        )
        payload = json.dumps(
            list(place_slugs),
            ensure_ascii=False,
            separators=(",", ":"),
        )

        async with connect_database(self.database_path) as database:
            await database.execute(
                """
                INSERT OR IGNORE INTO saved_routes (
                    user_id,
                    city_slug,
                    route_id,
                    interest,
                    budget_minutes,
                    place_slugs_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    city_slug,
                    route_id,
                    interest,
                    budget_minutes,
                    payload,
                ),
            )
            await database.commit()

        saved = await self.get(user_id, city_slug, route_id)
        if saved is None:
            raise RuntimeError("saved route was not persisted")
        return saved

    async def get(
        self,
        user_id: int,
        city_slug: str,
        route_id: str,
    ) -> SavedRoute | None:
        async with connect_database(self.database_path) as database:
            cursor = await database.execute(
                """
                SELECT
                    route_id,
                    city_slug,
                    interest,
                    budget_minutes,
                    place_slugs_json,
                    created_at
                FROM saved_routes
                WHERE user_id = ? AND city_slug = ? AND route_id = ?
                LIMIT 1
                """,
                (user_id, city_slug, route_id),
            )
            row = await cursor.fetchone()
            await cursor.close()

        return _saved_route_from_row(row) if row is not None else None

    async def list_routes(
        self,
        user_id: int,
        city_slug: str,
    ) -> tuple[SavedRoute, ...]:
        async with connect_database(self.database_path) as database:
            cursor = await database.execute(
                """
                SELECT
                    route_id,
                    city_slug,
                    interest,
                    budget_minutes,
                    place_slugs_json,
                    created_at
                FROM saved_routes
                WHERE user_id = ? AND city_slug = ?
                ORDER BY created_at DESC, route_id ASC
                """,
                (user_id, city_slug),
            )
            rows = await cursor.fetchall()
            await cursor.close()

        return tuple(_saved_route_from_row(row) for row in rows)

    async def remove(
        self,
        user_id: int,
        city_slug: str,
        route_id: str,
    ) -> None:
        async with connect_database(self.database_path) as database:
            await database.execute(
                """
                DELETE FROM saved_routes
                WHERE user_id = ? AND city_slug = ? AND route_id = ?
                """,
                (user_id, city_slug, route_id),
            )
            await database.commit()


def _decode_route_place_slugs(raw_payload: object, *, kind: str) -> tuple[str, ...]:
    try:
        raw_slugs = json.loads(str(raw_payload))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{kind} contains invalid place payload") from exc
    if (
        not isinstance(raw_slugs, list)
        or not raw_slugs
        or not all(isinstance(value, str) and value for value in raw_slugs)
        or len(set(raw_slugs)) != len(raw_slugs)
    ):
        raise RuntimeError(f"{kind} contains invalid place payload")
    return tuple(raw_slugs)


def _validate_route_values(
    *,
    city_slug: str,
    interest: str,
    budget_minutes: int,
    place_slugs: tuple[str, ...],
) -> None:
    if not city_slug:
        raise ValueError("route city must not be empty")
    if not interest:
        raise ValueError("route interest must not be empty")
    if budget_minutes <= 0:
        raise ValueError("route budget must be positive")
    if not place_slugs:
        raise ValueError("saved route must contain at least one place")
    if any(not slug for slug in place_slugs):
        raise ValueError("route place slug must not be empty")
    if len(set(place_slugs)) != len(place_slugs):
        raise ValueError("route places must be unique")


def _saved_route_from_row(row: tuple[object, ...]) -> SavedRoute:
    city_slug = str(row[1])
    interest = str(row[2])
    budget_minutes = int(row[3])
    place_slugs = _decode_route_place_slugs(row[4], kind="saved route")
    try:
        _validate_route_values(
            city_slug=city_slug,
            interest=interest,
            budget_minutes=budget_minutes,
            place_slugs=place_slugs,
        )
    except ValueError as exc:
        raise RuntimeError("saved route contains invalid metadata") from exc

    route_id = str(row[0])
    expected_route_id = route_id_for(
        city_slug,
        interest,
        budget_minutes,
        place_slugs,
    )
    if route_id != expected_route_id:
        raise RuntimeError("saved route id does not match persisted snapshot")

    return SavedRoute(
        route_id=route_id,
        city_slug=city_slug,
        interest=interest,
        budget_minutes=budget_minutes,
        place_slugs=place_slugs,
        created_at=str(row[5]),
    )



@dataclass(frozen=True, slots=True)
class CompletedRouteSnapshot:
    route_id: str
    city_slug: str
    interest: str
    budget_minutes: int
    place_slugs: tuple[str, ...]
    completed_at: str


class CompletedRoutesRepository:
    def __init__(self, database_path: str) -> None:
        self.database_path = Path(database_path)

    async def initialize(self) -> None:
        await migrate_database(self.database_path)

    async def complete_route(
        self,
        user_id: int,
        route: SavedRoute,
        available_place_slugs: set[str],
    ) -> tuple[int, int, int, bool]:
        _validate_route_values(
            city_slug=route.city_slug,
            interest=route.interest,
            budget_minutes=route.budget_minutes,
            place_slugs=route.place_slugs,
        )
        expected_route_id = route_id_for(
            route.city_slug,
            route.interest,
            route.budget_minutes,
            route.place_slugs,
        )
        if route.route_id != expected_route_id:
            raise ValueError("route id does not match route snapshot")

        available = tuple(
            slug for slug in route.place_slugs if slug in available_place_slugs
        )
        unavailable = len(route.place_slugs) - len(available)
        payload = json.dumps(
            list(route.place_slugs),
            ensure_ascii=False,
            separators=(",", ":"),
        )

        async with connect_database(self.database_path) as database:
            try:
                await database.execute("BEGIN IMMEDIATE")
                cursor = await database.execute(
                    """
                    SELECT 1
                    FROM completed_routes
                    WHERE user_id = ? AND city_slug = ? AND route_id = ?
                    LIMIT 1
                    """,
                    (user_id, route.city_slug, route.route_id),
                )
                already_completed = await cursor.fetchone() is not None
                await cursor.close()
                if already_completed:
                    await database.commit()
                    return 0, 0, unavailable, True

                already_visited = 0
                if available:
                    placeholders = ",".join("?" for _ in available)
                    cursor = await database.execute(
                        f"""
                        SELECT COUNT(*)
                        FROM visited_places
                        WHERE user_id = ? AND city_slug = ?
                          AND place_slug IN ({placeholders})
                        """,
                        (user_id, route.city_slug, *available),
                    )
                    row = await cursor.fetchone()
                    await cursor.close()
                    already_visited = int(row[0]) if row is not None else 0

                    await database.executemany(
                        """
                        INSERT OR IGNORE INTO visited_places (
                            user_id,
                            city_slug,
                            place_slug
                        )
                        VALUES (?, ?, ?)
                        """,
                        (
                            (user_id, route.city_slug, slug)
                            for slug in available
                        ),
                    )

                await database.execute(
                    """
                    INSERT OR IGNORE INTO completed_routes (
                        user_id,
                        city_slug,
                        route_id
                    )
                    VALUES (?, ?, ?)
                    """,
                    (user_id, route.city_slug, route.route_id),
                )
                await database.execute(
                    """
                    INSERT OR IGNORE INTO completed_route_snapshots (
                        user_id,
                        city_slug,
                        route_id,
                        interest,
                        budget_minutes,
                        place_slugs_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        route.city_slug,
                        route.route_id,
                        route.interest,
                        route.budget_minutes,
                        payload,
                    ),
                )
                await database.commit()
            except aiosqlite.Error:
                await database.rollback()
                raise

        return len(available) - already_visited, already_visited, unavailable, False

    async def list_snapshots(
        self,
        user_id: int,
        city_slug: str,
    ) -> tuple[CompletedRouteSnapshot, ...]:
        async with connect_database(self.database_path) as database:
            cursor = await database.execute(
                """
                SELECT
                    route_id,
                    city_slug,
                    interest,
                    budget_minutes,
                    place_slugs_json,
                    completed_at
                FROM completed_route_snapshots
                WHERE user_id = ? AND city_slug = ?
                ORDER BY completed_at DESC, route_id ASC
                """,
                (user_id, city_slug),
            )
            rows = await cursor.fetchall()
            await cursor.close()

        return tuple(_completed_route_snapshot_from_row(row) for row in rows)

    async def get_snapshot(
        self,
        user_id: int,
        city_slug: str,
        route_id: str,
    ) -> CompletedRouteSnapshot | None:
        snapshots = await self.list_snapshots(user_id, city_slug)
        return next((item for item in snapshots if item.route_id == route_id), None)

    async def contains(self, user_id: int, city_slug: str, route_id: str) -> bool:
        async with connect_database(self.database_path) as database:
            cursor = await database.execute(
                """
                SELECT 1
                FROM completed_routes
                WHERE user_id = ? AND city_slug = ? AND route_id = ?
                LIMIT 1
                """,
                (user_id, city_slug, route_id),
            )
            row = await cursor.fetchone()
            await cursor.close()
            return row is not None

    async def count(self, user_id: int, city_slug: str) -> int:
        async with connect_database(self.database_path) as database:
            cursor = await database.execute(
                """
                SELECT COUNT(*)
                FROM completed_routes
                WHERE user_id = ? AND city_slug = ?
                """,
                (user_id, city_slug),
            )
            row = await cursor.fetchone()
            await cursor.close()
            return int(row[0]) if row is not None else 0

    async def list_route_ids(self, user_id: int, city_slug: str) -> tuple[str, ...]:
        async with connect_database(self.database_path) as database:
            cursor = await database.execute(
                """
                SELECT route_id
                FROM completed_routes
                WHERE user_id = ? AND city_slug = ?
                ORDER BY completed_at DESC, route_id ASC
                """,
                (user_id, city_slug),
            )
            rows = await cursor.fetchall()
            await cursor.close()
            return tuple(str(row[0]) for row in rows)



def _completed_route_snapshot_from_row(
    row: tuple[object, ...],
) -> CompletedRouteSnapshot:
    city_slug = str(row[1])
    interest = str(row[2])
    budget_minutes = int(row[3])
    place_slugs = _decode_route_place_slugs(row[4], kind="completed route")
    try:
        _validate_route_values(
            city_slug=city_slug,
            interest=interest,
            budget_minutes=budget_minutes,
            place_slugs=place_slugs,
        )
    except ValueError as exc:
        raise RuntimeError("completed route contains invalid metadata") from exc
    route_id = str(row[0])
    expected_route_id = route_id_for(
        city_slug,
        interest,
        budget_minutes,
        place_slugs,
    )
    if route_id != expected_route_id:
        raise RuntimeError("completed route id does not match persisted snapshot")

    return CompletedRouteSnapshot(
        route_id=route_id,
        city_slug=city_slug,
        interest=interest,
        budget_minutes=budget_minutes,
        place_slugs=place_slugs,
        completed_at=str(row[5]),
    )


class DismissedRepository:
    def __init__(self, database_path: str) -> None:
        self.database_path = Path(database_path)

    async def initialize(self) -> None:
        await migrate_database(self.database_path)

    async def add(self, user_id: int, city_slug: str, place_slug: str) -> None:
        async with connect_database(self.database_path) as database:
            await database.execute(
                """
                INSERT OR IGNORE INTO dismissed_places (
                    user_id,
                    city_slug,
                    place_slug
                )
                VALUES (?, ?, ?)
                """,
                (user_id, city_slug, place_slug),
            )
            await database.commit()

    async def remove(self, user_id: int, city_slug: str, place_slug: str) -> None:
        async with connect_database(self.database_path) as database:
            await database.execute(
                """
                DELETE FROM dismissed_places
                WHERE user_id = ? AND city_slug = ? AND place_slug = ?
                """,
                (user_id, city_slug, place_slug),
            )
            await database.commit()

    async def contains(self, user_id: int, city_slug: str, place_slug: str) -> bool:
        async with connect_database(self.database_path) as database:
            cursor = await database.execute(
                """
                SELECT 1
                FROM dismissed_places
                WHERE user_id = ? AND city_slug = ? AND place_slug = ?
                LIMIT 1
                """,
                (user_id, city_slug, place_slug),
            )
            row = await cursor.fetchone()
            await cursor.close()
            return row is not None

    async def list_place_slugs(self, user_id: int, city_slug: str) -> tuple[str, ...]:
        async with connect_database(self.database_path) as database:
            cursor = await database.execute(
                """
                SELECT place_slug
                FROM dismissed_places
                WHERE user_id = ? AND city_slug = ?
                ORDER BY dismissed_at DESC, place_slug ASC
                """,
                (user_id, city_slug),
            )
            rows = await cursor.fetchall()
            await cursor.close()
            return tuple(str(row[0]) for row in rows)


@dataclass(frozen=True, slots=True)
class UserDataSnapshot:
    interests: tuple[str, ...]
    dismissed_slugs: tuple[str, ...]
    favorite_slugs: tuple[str, ...]
    visited_slugs: tuple[str, ...]
    saved_routes: tuple[SavedRoute, ...]
    completed_routes: tuple[CompletedRouteSnapshot, ...]


class UserDataSnapshotRepository:
    """Read exportable user data from one consistent SQLite snapshot."""

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)

    async def load(self, user_id: int, city_slug: str) -> UserDataSnapshot:
        async with connect_database(self.database_path) as database:
            await database.execute("BEGIN")
            try:
                interests = await _read_single_column(
                    database,
                    """
                    SELECT interest FROM user_interests
                    WHERE user_id = ? AND city_slug = ?
                    ORDER BY interest ASC
                    """,
                    (user_id, city_slug),
                )
                dismissed = await _read_single_column(
                    database,
                    """
                    SELECT place_slug FROM dismissed_places
                    WHERE user_id = ? AND city_slug = ?
                    ORDER BY dismissed_at DESC, place_slug ASC
                    """,
                    (user_id, city_slug),
                )
                favorites = await _read_single_column(
                    database,
                    """
                    SELECT place_slug FROM favorites
                    WHERE user_id = ? AND city_slug = ?
                    ORDER BY created_at DESC, place_slug ASC
                    """,
                    (user_id, city_slug),
                )
                visited = await _read_single_column(
                    database,
                    """
                    SELECT place_slug FROM visited_places
                    WHERE user_id = ? AND city_slug = ?
                    ORDER BY visited_at DESC, place_slug ASC
                    """,
                    (user_id, city_slug),
                )

                cursor = await database.execute(
                    """
                    SELECT route_id, city_slug, interest, budget_minutes,
                           place_slugs_json, created_at
                    FROM saved_routes
                    WHERE user_id = ? AND city_slug = ?
                    ORDER BY created_at DESC, route_id ASC
                    """,
                    (user_id, city_slug),
                )
                saved_rows = await cursor.fetchall()
                await cursor.close()

                cursor = await database.execute(
                    """
                    SELECT route_id, city_slug, interest, budget_minutes,
                           place_slugs_json, completed_at
                    FROM completed_route_snapshots
                    WHERE user_id = ? AND city_slug = ?
                    ORDER BY completed_at DESC, route_id ASC
                    """,
                    (user_id, city_slug),
                )
                completed_rows = await cursor.fetchall()
                await cursor.close()
                await database.commit()
            except Exception:
                await database.rollback()
                raise

        return UserDataSnapshot(
            interests=interests,
            dismissed_slugs=dismissed,
            favorite_slugs=favorites,
            visited_slugs=visited,
            saved_routes=tuple(_saved_route_from_row(row) for row in saved_rows),
            completed_routes=tuple(
                _completed_route_snapshot_from_row(row) for row in completed_rows
            ),
        )


async def _read_single_column(
    database: aiosqlite.Connection,
    query: str,
    parameters: tuple[object, ...],
) -> tuple[str, ...]:
    cursor = await database.execute(query, parameters)
    rows = await cursor.fetchall()
    await cursor.close()
    return tuple(str(row[0]) for row in rows)

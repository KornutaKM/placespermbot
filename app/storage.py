import json
from pathlib import Path

import aiosqlite

from app.database import migrate_database
from app.saved_routes import SavedRoute, route_id_for


class FavoritesRepository:
    def __init__(self, database_path: str) -> None:
        self.database_path = Path(database_path)

    async def initialize(self) -> None:
        await migrate_database(self.database_path)

    async def add(self, user_id: int, city_slug: str, place_slug: str) -> None:
        async with aiosqlite.connect(self.database_path) as database:
            await database.execute(
                """
                INSERT OR IGNORE INTO favorites (user_id, city_slug, place_slug)
                VALUES (?, ?, ?)
                """,
                (user_id, city_slug, place_slug),
            )
            await database.commit()

    async def remove(self, user_id: int, city_slug: str, place_slug: str) -> None:
        async with aiosqlite.connect(self.database_path) as database:
            await database.execute(
                """
                DELETE FROM favorites
                WHERE user_id = ? AND city_slug = ? AND place_slug = ?
                """,
                (user_id, city_slug, place_slug),
            )
            await database.commit()

    async def contains(self, user_id: int, city_slug: str, place_slug: str) -> bool:
        async with aiosqlite.connect(self.database_path) as database:
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
        async with aiosqlite.connect(self.database_path) as database:
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
        async with aiosqlite.connect(self.database_path) as database:
            await database.execute(
                """
                INSERT OR IGNORE INTO user_interests (user_id, city_slug, interest)
                VALUES (?, ?, ?)
                """,
                (user_id, city_slug, interest),
            )
            await database.commit()

    async def remove(self, user_id: int, city_slug: str, interest: str) -> None:
        async with aiosqlite.connect(self.database_path) as database:
            await database.execute(
                """
                DELETE FROM user_interests
                WHERE user_id = ? AND city_slug = ? AND interest = ?
                """,
                (user_id, city_slug, interest),
            )
            await database.commit()

    async def list_interests(self, user_id: int, city_slug: str) -> tuple[str, ...]:
        async with aiosqlite.connect(self.database_path) as database:
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
        async with aiosqlite.connect(self.database_path) as database:
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
        async with aiosqlite.connect(self.database_path) as database:
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
        async with aiosqlite.connect(self.database_path) as database:
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
        async with aiosqlite.connect(self.database_path) as database:
            await database.execute(
                """
                DELETE FROM visited_places
                WHERE user_id = ? AND city_slug = ? AND place_slug = ?
                """,
                (user_id, city_slug, place_slug),
            )
            await database.commit()

    async def contains(self, user_id: int, city_slug: str, place_slug: str) -> bool:
        async with aiosqlite.connect(self.database_path) as database:
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
        async with aiosqlite.connect(self.database_path) as database:
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
        if not place_slugs:
            raise ValueError("saved route must contain at least one place")

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

        async with aiosqlite.connect(self.database_path) as database:
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
        async with aiosqlite.connect(self.database_path) as database:
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
        async with aiosqlite.connect(self.database_path) as database:
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
        async with aiosqlite.connect(self.database_path) as database:
            await database.execute(
                """
                DELETE FROM saved_routes
                WHERE user_id = ? AND city_slug = ? AND route_id = ?
                """,
                (user_id, city_slug, route_id),
            )
            await database.commit()


def _saved_route_from_row(row: tuple[object, ...]) -> SavedRoute:
    raw_slugs = json.loads(str(row[4]))
    if not isinstance(raw_slugs, list) or not all(
        isinstance(value, str) and value
        for value in raw_slugs
    ):
        raise RuntimeError("saved route contains invalid place payload")

    return SavedRoute(
        route_id=str(row[0]),
        city_slug=str(row[1]),
        interest=str(row[2]),
        budget_minutes=int(row[3]),
        place_slugs=tuple(raw_slugs),
        created_at=str(row[5]),
    )



class CompletedRoutesRepository:
    def __init__(self, database_path: str) -> None:
        self.database_path = Path(database_path)

    async def initialize(self) -> None:
        await migrate_database(self.database_path)

    async def add(self, user_id: int, city_slug: str, route_id: str) -> None:
        async with aiosqlite.connect(self.database_path) as database:
            await database.execute(
                """
                INSERT OR IGNORE INTO completed_routes (
                    user_id,
                    city_slug,
                    route_id
                )
                VALUES (?, ?, ?)
                """,
                (user_id, city_slug, route_id),
            )
            await database.commit()

    async def contains(self, user_id: int, city_slug: str, route_id: str) -> bool:
        async with aiosqlite.connect(self.database_path) as database:
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
        async with aiosqlite.connect(self.database_path) as database:
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
        async with aiosqlite.connect(self.database_path) as database:
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


class DismissedRepository:
    def __init__(self, database_path: str) -> None:
        self.database_path = Path(database_path)

    async def initialize(self) -> None:
        await migrate_database(self.database_path)

    async def add(self, user_id: int, city_slug: str, place_slug: str) -> None:
        async with aiosqlite.connect(self.database_path) as database:
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
        async with aiosqlite.connect(self.database_path) as database:
            await database.execute(
                """
                DELETE FROM dismissed_places
                WHERE user_id = ? AND city_slug = ? AND place_slug = ?
                """,
                (user_id, city_slug, place_slug),
            )
            await database.commit()

    async def contains(self, user_id: int, city_slug: str, place_slug: str) -> bool:
        async with aiosqlite.connect(self.database_path) as database:
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
        async with aiosqlite.connect(self.database_path) as database:
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

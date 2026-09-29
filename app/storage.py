from pathlib import Path

import aiosqlite

from app.database import migrate_database


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

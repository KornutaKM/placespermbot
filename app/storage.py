from pathlib import Path

import aiosqlite


class FavoritesRepository:
    def __init__(self, database_path: str) -> None:
        self.database_path = Path(database_path)

    async def initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.database_path) as database:
            await database.execute(
                """
                CREATE TABLE IF NOT EXISTS favorites (
                    user_id INTEGER NOT NULL,
                    city_slug TEXT NOT NULL,
                    place_slug TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, city_slug, place_slug)
                )
                """
            )
            await database.commit()

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
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.database_path) as database:
            await database.execute(
                """
                CREATE TABLE IF NOT EXISTS user_interests (
                    user_id INTEGER NOT NULL,
                    city_slug TEXT NOT NULL,
                    interest TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, city_slug, interest)
                )
                """
            )
            await database.commit()

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
                ORDER BY created_at ASC, interest ASC
                """,
                (user_id, city_slug),
            )
            rows = await cursor.fetchall()
            await cursor.close()
            return tuple(str(row[0]) for row in rows)

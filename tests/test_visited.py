import asyncio

from app.database import migrate_database
from app.storage import FavoritesRepository, VisitedRepository


def test_visited_round_trip(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        repository = VisitedRepository(database_path)

        assert not await repository.contains(42, "saint-petersburg", "hermitage")

        await repository.add(42, "saint-petersburg", "hermitage")

        assert await repository.contains(42, "saint-petersburg", "hermitage")
        assert await repository.list_place_slugs(42, "saint-petersburg") == (
            "hermitage",
        )

        await repository.remove(42, "saint-petersburg", "hermitage")

        assert not await repository.contains(42, "saint-petersburg", "hermitage")
        assert await repository.list_place_slugs(42, "saint-petersburg") == ()

    asyncio.run(scenario())


def test_visited_add_is_idempotent(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        repository = VisitedRepository(database_path)

        await repository.add(7, "saint-petersburg", "palace-square")
        await repository.add(7, "saint-petersburg", "palace-square")

        assert await repository.list_place_slugs(7, "saint-petersburg") == (
            "palace-square",
        )

    asyncio.run(scenario())


def test_visited_is_scoped_by_user_and_city(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        repository = VisitedRepository(database_path)

        await repository.add(1, "saint-petersburg", "hermitage")
        await repository.add(1, "another-city", "other-place")
        await repository.add(2, "saint-petersburg", "palace-square")

        assert await repository.list_place_slugs(1, "saint-petersburg") == (
            "hermitage",
        )
        assert await repository.list_place_slugs(1, "another-city") == (
            "other-place",
        )
        assert await repository.list_place_slugs(2, "saint-petersburg") == (
            "palace-square",
        )

    asyncio.run(scenario())


def test_visited_and_favorites_are_independent(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        visited = VisitedRepository(database_path)
        favorites = FavoritesRepository(database_path)

        await favorites.add(5, "saint-petersburg", "hermitage")
        await visited.add(5, "saint-petersburg", "hermitage")
        await visited.remove(5, "saint-petersburg", "hermitage")

        assert await favorites.contains(5, "saint-petersburg", "hermitage")
        assert not await visited.contains(5, "saint-petersburg", "hermitage")

    asyncio.run(scenario())

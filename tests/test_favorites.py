import asyncio

from app.storage import FavoritesRepository


def test_favorites_round_trip(tmp_path) -> None:
    async def scenario() -> None:
        repository = FavoritesRepository(str(tmp_path / "favorites.db"))
        await repository.initialize()

        assert not await repository.contains(42, "saint-petersburg", "hermitage")

        await repository.add(42, "saint-petersburg", "hermitage")
        assert await repository.contains(42, "saint-petersburg", "hermitage")
        assert await repository.list_place_slugs(42, "saint-petersburg") == ("hermitage",)

        await repository.remove(42, "saint-petersburg", "hermitage")
        assert not await repository.contains(42, "saint-petersburg", "hermitage")
        assert await repository.list_place_slugs(42, "saint-petersburg") == ()

    asyncio.run(scenario())


def test_add_is_idempotent(tmp_path) -> None:
    async def scenario() -> None:
        repository = FavoritesRepository(str(tmp_path / "favorites.db"))
        await repository.initialize()

        await repository.add(7, "saint-petersburg", "palace-square")
        await repository.add(7, "saint-petersburg", "palace-square")

        assert await repository.list_place_slugs(7, "saint-petersburg") == (
            "palace-square",
        )

    asyncio.run(scenario())


def test_favorites_are_scoped_by_user_and_city(tmp_path) -> None:
    async def scenario() -> None:
        repository = FavoritesRepository(str(tmp_path / "favorites.db"))
        await repository.initialize()

        await repository.add(1, "saint-petersburg", "hermitage")
        await repository.add(1, "another-city", "other-place")
        await repository.add(2, "saint-petersburg", "palace-square")

        assert await repository.list_place_slugs(1, "saint-petersburg") == ("hermitage",)
        assert await repository.list_place_slugs(1, "another-city") == ("other-place",)
        assert await repository.list_place_slugs(2, "saint-petersburg") == (
            "palace-square",
        )

    asyncio.run(scenario())

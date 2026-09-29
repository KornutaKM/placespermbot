import asyncio

from app.storage import InterestsRepository


def test_interests_round_trip(tmp_path) -> None:
    async def scenario() -> None:
        repository = InterestsRepository(str(tmp_path / "places.db"))
        await repository.initialize()

        assert await repository.list_interests(1, "saint-petersburg") == ()

        await repository.add(1, "saint-petersburg", "museums")
        await repository.add(1, "saint-petersburg", "free")

        assert await repository.list_interests(1, "saint-petersburg") == (
            "free",
            "museums",
        )

        await repository.remove(1, "saint-petersburg", "museums")

        assert await repository.list_interests(1, "saint-petersburg") == ("free",)

    asyncio.run(scenario())


def test_interest_add_is_idempotent(tmp_path) -> None:
    async def scenario() -> None:
        repository = InterestsRepository(str(tmp_path / "places.db"))
        await repository.initialize()

        await repository.add(7, "saint-petersburg", "architecture")
        await repository.add(7, "saint-petersburg", "architecture")

        assert await repository.list_interests(7, "saint-petersburg") == (
            "architecture",
        )

    asyncio.run(scenario())


def test_interests_are_scoped_by_user_and_city(tmp_path) -> None:
    async def scenario() -> None:
        repository = InterestsRepository(str(tmp_path / "places.db"))
        await repository.initialize()

        await repository.add(1, "saint-petersburg", "museums")
        await repository.add(1, "another-city", "walks")
        await repository.add(2, "saint-petersburg", "free")

        assert await repository.list_interests(1, "saint-petersburg") == ("museums",)
        assert await repository.list_interests(1, "another-city") == ("walks",)
        assert await repository.list_interests(2, "saint-petersburg") == ("free",)

    asyncio.run(scenario())

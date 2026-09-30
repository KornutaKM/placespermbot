import asyncio

from app.data.spb import CITY_SLUG
from app.database import migrate_database
from app.storage import DismissedRepository


def test_dismissed_round_trip_and_idempotency(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        repository = DismissedRepository(database_path)

        assert not await repository.contains(1, CITY_SLUG, "hermitage")

        await repository.add(1, CITY_SLUG, "hermitage")
        await repository.add(1, CITY_SLUG, "hermitage")

        assert await repository.contains(1, CITY_SLUG, "hermitage")
        assert await repository.list_place_slugs(1, CITY_SLUG) == ("hermitage",)

        await repository.remove(1, CITY_SLUG, "hermitage")
        await repository.remove(1, CITY_SLUG, "hermitage")

        assert not await repository.contains(1, CITY_SLUG, "hermitage")
        assert await repository.list_place_slugs(1, CITY_SLUG) == ()

    asyncio.run(scenario())


def test_dismissed_are_scoped_by_user_and_city(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        repository = DismissedRepository(database_path)

        await repository.add(1, CITY_SLUG, "hermitage")
        await repository.add(1, "another-city", "other-place")
        await repository.add(2, CITY_SLUG, "summer-garden")

        assert await repository.list_place_slugs(1, CITY_SLUG) == ("hermitage",)
        assert await repository.list_place_slugs(1, "another-city") == ("other-place",)
        assert await repository.list_place_slugs(2, CITY_SLUG) == ("summer-garden",)

    asyncio.run(scenario())

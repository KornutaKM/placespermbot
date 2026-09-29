import asyncio

import pytest

from app.catalog_service import CatalogService
from app.database import migrate_database
from app.storage import UserCityRepository


def test_user_city_round_trip_and_isolation(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        repository = UserCityRepository(database_path)

        assert await repository.get_city_slug(1) is None
        assert await repository.get_city_slug(2) is None

        await repository.set_city_slug(1, "saint-petersburg")

        assert await repository.get_city_slug(1) == "saint-petersburg"
        assert await repository.get_city_slug(2) is None

    asyncio.run(scenario())


def test_user_city_upsert_replaces_previous_value(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        repository = UserCityRepository(database_path)

        await repository.set_city_slug(7, "old-city")
        await repository.set_city_slug(7, "saint-petersburg")

        assert await repository.get_city_slug(7) == "saint-petersburg"

    asyncio.run(scenario())


def test_catalog_service_uses_default_without_preference(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        service = CatalogService(
            default_city_slug="saint-petersburg",
            user_city_repo=UserCityRepository(database_path),
        )

        catalog = await service.for_user(42)

        assert catalog.slug == "saint-petersburg"

    asyncio.run(scenario())


def test_catalog_service_persists_supported_city(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        repository = UserCityRepository(database_path)
        service = CatalogService(
            default_city_slug="saint-petersburg",
            user_city_repo=repository,
        )

        selected = await service.set_for_user(42, "saint-petersburg")
        resolved = await service.for_user(42)

        assert selected.slug == "saint-petersburg"
        assert resolved.slug == "saint-petersburg"
        assert await repository.get_city_slug(42) == "saint-petersburg"

    asyncio.run(scenario())


def test_catalog_service_rejects_unsupported_city(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        repository = UserCityRepository(database_path)
        service = CatalogService(
            default_city_slug="saint-petersburg",
            user_city_repo=repository,
        )

        with pytest.raises(RuntimeError, match="Unsupported city"):
            await service.set_for_user(42, "unknown-city")

        assert await repository.get_city_slug(42) is None

    asyncio.run(scenario())


def test_stale_preference_falls_back_to_default(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        repository = UserCityRepository(database_path)
        service = CatalogService(
            default_city_slug="saint-petersburg",
            user_city_repo=repository,
        )
        await repository.set_city_slug(42, "removed-city")

        catalog = await service.for_user(42)

        assert catalog.slug == "saint-petersburg"

    asyncio.run(scenario())

import asyncio

import pytest

from app.config import Settings
from app.runtime_checks import validate_health, validate_static_runtime
from app.storage import FavoritesRepository, InterestsRepository


def settings(tmp_path, **overrides) -> Settings:
    values = {
        "bot_token": "123456789:test-token",
        "city_slug": "saint-petersburg",
        "database_path": str(tmp_path / "places.db"),
        "environment": "test",
    }
    values.update(overrides)
    return Settings(**values)


def test_static_runtime_accepts_valid_config(tmp_path) -> None:
    validate_static_runtime(settings(tmp_path))


def test_static_runtime_rejects_missing_token(tmp_path) -> None:
    with pytest.raises(RuntimeError, match="PLACES_BOT_TOKEN"):
        validate_static_runtime(settings(tmp_path, bot_token="replace-me"))


def test_static_runtime_rejects_unknown_city(tmp_path) -> None:
    with pytest.raises(RuntimeError, match="Unsupported city"):
        validate_static_runtime(settings(tmp_path, city_slug="unknown-city"))


def test_health_accepts_initialized_database(tmp_path) -> None:
    async def scenario() -> None:
        config = settings(tmp_path)
        favorites = FavoritesRepository(config.database_path)
        interests = InterestsRepository(config.database_path)
        await favorites.initialize()
        await interests.initialize()

        await validate_health(config)

    asyncio.run(scenario())


def test_health_rejects_missing_database(tmp_path) -> None:
    async def scenario() -> None:
        with pytest.raises(RuntimeError, match="Database is not initialized"):
            await validate_health(settings(tmp_path))

    asyncio.run(scenario())


def test_health_rejects_incomplete_schema(tmp_path) -> None:
    async def scenario() -> None:
        config = settings(tmp_path)
        favorites = FavoritesRepository(config.database_path)
        await favorites.initialize()

        with pytest.raises(RuntimeError, match="user_interests"):
            await validate_health(config)

    asyncio.run(scenario())

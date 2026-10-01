import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import Settings
from app.main import main


def test_startup_fails_before_telegram_when_runtime_health_is_invalid(tmp_path) -> None:
    settings = Settings(
        bot_token="123456789:test-token",
        environment="test",
        city_slug="saint-petersburg",
        database_path=str(tmp_path / "places.db"),
    )

    migrate_database = AsyncMock()
    validate_health = AsyncMock(side_effect=RuntimeError("Database schema drift"))
    bot = MagicMock()

    async def scenario() -> None:
        with (
            patch("app.main.get_settings", return_value=settings),
            patch("app.main.migrate_database", migrate_database),
            patch("app.main.validate_health", validate_health),
            patch("app.main.Bot", bot),
            pytest.raises(RuntimeError, match="Database schema drift"),
        ):
            await main()

    asyncio.run(scenario())

    migrate_database.assert_awaited_once_with(settings.database_path)
    validate_health.assert_awaited_once_with(settings)
    bot.assert_not_called()

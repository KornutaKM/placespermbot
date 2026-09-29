import asyncio
from types import SimpleNamespace

import pytest

from app.catalog_context import CatalogMiddleware, get_current_catalog
from app.catalog_service import CatalogService
from app.database import migrate_database
from app.storage import UserCityRepository


def test_catalog_middleware_sets_and_resets_request_context(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        service = CatalogService(
            default_city_slug="saint-petersburg",
            user_city_repo=UserCityRepository(database_path),
        )
        middleware = CatalogMiddleware(service)
        observed: list[str] = []

        async def handler(event, data):
            observed.append(get_current_catalog().slug)
            assert data["catalog_service"] is service
            return "ok"

        result = await middleware(
            handler,
            object(),
            {"event_from_user": SimpleNamespace(id=42)},
        )

        assert result == "ok"
        assert observed == ["saint-petersburg"]

        with pytest.raises(RuntimeError, match="outside Telegram update context"):
            get_current_catalog()

    asyncio.run(scenario())

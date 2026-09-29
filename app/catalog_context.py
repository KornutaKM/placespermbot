from __future__ import annotations

from contextvars import ContextVar
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.catalog import CityCatalog
from app.catalog_service import CatalogService

_current_catalog: ContextVar[CityCatalog | None] = ContextVar(
    "current_catalog",
    default=None,
)


def get_current_catalog() -> CityCatalog:
    catalog = _current_catalog.get()
    if catalog is None:
        raise RuntimeError("Current catalog is unavailable outside Telegram update context")
    return catalog


class CatalogMiddleware(BaseMiddleware):
    def __init__(self, catalog_service: CatalogService) -> None:
        self.catalog_service = catalog_service

    async def __call__(
        self,
        handler: Callable[
            [TelegramObject, dict[str, Any]],
            Awaitable[Any],
        ],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is None:
            return await handler(event, data)

        catalog = await self.catalog_service.for_user(user.id)
        token = _current_catalog.set(catalog)
        data["catalog_service"] = self.catalog_service
        try:
            return await handler(event, data)
        finally:
            _current_catalog.reset(token)

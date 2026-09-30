from __future__ import annotations

from dataclasses import dataclass

from app.catalog import CityCatalog, get_catalog, list_catalogs
from app.storage import UserCityRepository


@dataclass(slots=True)
class CatalogService:
    default_city_slug: str
    user_city_repo: UserCityRepository

    async def selected_for_user(self, user_id: int) -> CityCatalog | None:
        city_slug = await self.user_city_repo.get_city_slug(user_id)
        if city_slug is None:
            return None

        try:
            return get_catalog(city_slug)
        except RuntimeError:
            return None

    async def for_user(self, user_id: int) -> CityCatalog:
        selected = await self.selected_for_user(user_id)
        if selected is not None:
            return selected
        return get_catalog(self.default_city_slug)

    async def set_for_user(self, user_id: int, city_slug: str) -> CityCatalog:
        catalog = get_catalog(city_slug)
        await self.user_city_repo.set_city_slug(user_id, catalog.slug)
        return catalog

    def available_catalogs(self) -> tuple[CityCatalog, ...]:
        return list_catalogs()

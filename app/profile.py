from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.catalog import CityCatalog
from app.planner import INTEREST_LABELS
from app.storage import (
    FavoritesRepository,
    InterestsRepository,
    SavedRoutesRepository,
    VisitedRepository,
)


@dataclass(frozen=True, slots=True)
class ProfileSummary:
    city_name: str
    interest_labels: tuple[str, ...]
    favorites_count: int
    visited_count: int
    saved_routes_count: int

    @property
    def interests_text(self) -> str:
        if not self.interest_labels:
            return "не выбраны"
        return " · ".join(self.interest_labels)


async def build_profile_summary(
    user_id: int,
    catalog: CityCatalog,
    *,
    favorites_repo: FavoritesRepository,
    interests_repo: InterestsRepository,
    visited_repo: VisitedRepository,
    saved_routes_repo: SavedRoutesRepository,
) -> ProfileSummary:
    interests, favorite_slugs, visited_slugs, saved_routes = await asyncio.gather(
        interests_repo.list_interests(user_id, catalog.slug),
        favorites_repo.list_place_slugs(user_id, catalog.slug),
        visited_repo.list_place_slugs(user_id, catalog.slug),
        saved_routes_repo.list_routes(user_id, catalog.slug),
    )

    labels = tuple(
        INTEREST_LABELS.get(interest, interest)
        for interest in interests
    )
    return ProfileSummary(
        city_name=catalog.name,
        interest_labels=labels,
        favorites_count=len(favorite_slugs),
        visited_count=len(visited_slugs),
        saved_routes_count=len(saved_routes),
    )


def profile_text(summary: ProfileSummary) -> str:
    return (
        "👤 <b>Мой гид</b>\n\n"
        f"🌆 Город: <b>{summary.city_name}</b>\n"
        f"🎯 Интересы: {summary.interests_text}\n"
        f"❤️ Избранное: {summary.favorites_count}\n"
        f"✅ Посещённые: {summary.visited_count}\n"
        f"🧭 Сохранённые маршруты: {summary.saved_routes_count}\n\n"
        "Все данные относятся к активному городу и основаны только "
        "на ваших явных действиях в боте."
    )

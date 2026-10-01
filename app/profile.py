from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.catalog import CityCatalog
from app.planner import INTEREST_LABELS
from app.storage import (
    CompletedRoutesRepository,
    DismissedRepository,
    FavoritesRepository,
    InterestsRepository,
    SavedRoutesRepository,
    VisitedRepository,
)


@dataclass(frozen=True, slots=True)
class ProfileSummary:
    city_name: str
    interest_labels: tuple[str, ...]
    dismissed_count: int
    favorites_count: int
    visited_count: int
    saved_routes_count: int
    completed_routes_count: int
    catalog_places_count: int
    progress_percent: int
    achievement_labels: tuple[str, ...]

    @property
    def interests_text(self) -> str:
        if not self.interest_labels:
            return "не выбраны"
        return " · ".join(self.interest_labels)

    @property
    def achievements_text(self) -> str:
        if not self.achievement_labels:
            return "пока нет"
        return " · ".join(self.achievement_labels)


async def build_profile_summary(
    user_id: int,
    catalog: CityCatalog,
    *,
    dismissed_repo: DismissedRepository,
    favorites_repo: FavoritesRepository,
    interests_repo: InterestsRepository,
    visited_repo: VisitedRepository,
    saved_routes_repo: SavedRoutesRepository,
    completed_routes_repo: CompletedRoutesRepository | None = None,
) -> ProfileSummary:
    (
        interests,
        dismissed_slugs,
        favorite_slugs,
        visited_slugs,
        saved_routes,
        completed_routes,
    ) = await asyncio.gather(
        interests_repo.list_interests(user_id, catalog.slug),
        dismissed_repo.list_place_slugs(user_id, catalog.slug),
        favorites_repo.list_place_slugs(user_id, catalog.slug),
        visited_repo.list_place_slugs(user_id, catalog.slug),
        saved_routes_repo.list_routes(user_id, catalog.slug),
        (
            completed_routes_repo.list_snapshots(user_id, catalog.slug)
            if completed_routes_repo is not None
            else _empty_completed_routes()
        ),
    )

    available_slugs = {place.slug for place in catalog.places}
    available_visited = available_slugs.intersection(visited_slugs)
    visited_count = len(available_visited)
    catalog_places_count = len(catalog.places)
    progress_percent = (
        round(visited_count * 100 / catalog_places_count)
        if catalog_places_count
        else 0
    )

    completed_routes_count = len(completed_routes)
    labels = tuple(INTEREST_LABELS.get(interest, interest) for interest in interests)
    achievements: list[str] = []
    if visited_count >= 1:
        achievements.append("🏅 Первое открытие")
    if progress_percent >= 25:
        achievements.append("🧭 Исследователь города")
    if len(favorite_slugs) >= 5:
        achievements.append("❤️ Коллекционер")
    if len(saved_routes) >= 3:
        achievements.append("🗺 Планировщик")
    if completed_routes_count >= 1:
        achievements.append("🏁 Первый маршрут")
    if completed_routes_count >= 3:
        achievements.append("🥾 Маршрутный исследователь")

    return ProfileSummary(
        city_name=catalog.name,
        interest_labels=labels,
        dismissed_count=len(dismissed_slugs),
        favorites_count=len(favorite_slugs),
        visited_count=visited_count,
        saved_routes_count=len(saved_routes),
        completed_routes_count=completed_routes_count,
        catalog_places_count=catalog_places_count,
        progress_percent=progress_percent,
        achievement_labels=tuple(achievements),
    )


def _progress_bar(percent: int) -> str:
    filled = min(10, max(0, percent) // 10)
    return "█" * filled + "░" * (10 - filled)


def profile_text(summary: ProfileSummary) -> str:
    return (
        "👤 <b>Мой гид</b>\n\n"
        f"🌆 Город: <b>{summary.city_name}</b>\n"
        f"🎯 Интересы: {summary.interests_text}\n\n"
        "<b>Прогресс</b>\n"
        f"{_progress_bar(summary.progress_percent)} {summary.progress_percent}%\n"
        f"✅ Посещено: {summary.visited_count}/{summary.catalog_places_count}\n"
        f"❤️ Избранное: {summary.favorites_count}\n"
        f"🙈 Не интересно: {summary.dismissed_count}\n"
        f"🧭 Сохранённые маршруты: {summary.saved_routes_count}\n"
        f"🏁 Пройденные маршруты: {summary.completed_routes_count}\n\n"
        f"<b>Достижения</b>\n{summary.achievements_text}\n\n"
        "Все данные относятся к активному городу и основаны только "
        "на ваших явных действиях в боте."
    )


async def _empty_completed_routes() -> tuple[()]:
    return ()

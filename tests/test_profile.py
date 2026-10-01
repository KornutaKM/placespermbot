import asyncio

from app.catalog import get_catalog
from app.data.spb import CITY_SLUG
from app.database import migrate_database
from app.planner import INTEREST_LABELS
from app.profile import build_profile_summary, profile_text
from app.storage import (
    CompletedRoutesRepository,
    DismissedRepository,
    FavoritesRepository,
    InterestsRepository,
    SavedRoute,
    SavedRoutesRepository,
    VisitedRepository,
)


def test_profile_summary_is_scoped_by_user_and_city(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)

        dismissed = DismissedRepository(database_path)
        favorites = FavoritesRepository(database_path)
        interests = InterestsRepository(database_path)
        visited = VisitedRepository(database_path)
        saved_routes = SavedRoutesRepository(database_path)
        completed_routes = CompletedRoutesRepository(database_path)

        await dismissed.add(1, CITY_SLUG, "new-holland")
        await dismissed.add(1, "another-city", "other-place")
        await dismissed.add(2, CITY_SLUG, "summer-garden")

        await favorites.add(1, CITY_SLUG, "hermitage")
        await favorites.add(1, "another-city", "other-place")
        await favorites.add(2, CITY_SLUG, "palace-square")

        await visited.add(1, CITY_SLUG, "summer-garden")
        await visited.add(1, "another-city", "other-place")
        await visited.add(2, CITY_SLUG, "hermitage")

        await interests.add(1, CITY_SLUG, "museums")
        await interests.add(1, CITY_SLUG, "walks")
        await interests.add(1, "another-city", "free")
        await interests.add(2, CITY_SLUG, "architecture")

        await saved_routes.save(
            1,
            CITY_SLUG,
            "museums",
            240,
            ("hermitage", "russian-museum"),
        )
        completed_route = SavedRoute(
            route_id="completed-route",
            city_slug=CITY_SLUG,
            interest="museums",
            budget_minutes=120,
            place_slugs=("hermitage",),
            created_at="2026-10-01 00:00:00",
        )
        await completed_routes.add(1, CITY_SLUG, completed_route.route_id)
        await completed_routes.add_snapshot(1, completed_route)
        await completed_routes.add(1, "another-city", "other-completed")
        await completed_routes.add(2, CITY_SLUG, "foreign-completed")

        await saved_routes.save(
            1,
            "another-city",
            "free",
            120,
            ("other-place",),
        )

        summary = await build_profile_summary(
            1,
            get_catalog(CITY_SLUG),
            dismissed_repo=dismissed,
            favorites_repo=favorites,
            interests_repo=interests,
            visited_repo=visited,
            saved_routes_repo=saved_routes,
            completed_routes_repo=completed_routes,
        )

        assert summary.city_name == "Санкт-Петербург"
        assert summary.dismissed_count == 1
        assert summary.favorites_count == 1
        assert summary.visited_count == 1
        assert summary.saved_routes_count == 1
        assert summary.completed_routes_count == 1
        assert summary.interest_labels == (
            INTEREST_LABELS["museums"],
            INTEREST_LABELS["walks"],
        )
        assert "🏁 Первый маршрут" in summary.achievement_labels

    asyncio.run(scenario())


def test_profile_summary_handles_empty_state(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)

        summary = await build_profile_summary(
            99,
            get_catalog(CITY_SLUG),
            dismissed_repo=DismissedRepository(database_path),
            favorites_repo=FavoritesRepository(database_path),
            interests_repo=InterestsRepository(database_path),
            visited_repo=VisitedRepository(database_path),
            saved_routes_repo=SavedRoutesRepository(database_path),
        )

        assert summary.interests_text == "не выбраны"
        assert summary.dismissed_count == 0
        assert summary.favorites_count == 0
        assert summary.visited_count == 0
        assert summary.saved_routes_count == 0

        text = profile_text(summary)
        assert "Интересы: не выбраны" in text
        assert "Избранное: 0" in text
        assert "Посещено: 0/" in text
        assert "0%" in text
        assert "Достижения" in text
        assert "пока нет" in text
        assert "Не интересно: 0" in text
        assert "Сохранённые маршруты: 0" in text

    asyncio.run(scenario())


def test_profile_progress_ignores_stale_visited_places(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        catalog = get_catalog(CITY_SLUG)
        visited = VisitedRepository(database_path)
        await visited.add(7, CITY_SLUG, catalog.places[0].slug)
        await visited.add(7, CITY_SLUG, "removed-place")

        summary = await build_profile_summary(
            7,
            catalog,
            dismissed_repo=DismissedRepository(database_path),
            favorites_repo=FavoritesRepository(database_path),
            interests_repo=InterestsRepository(database_path),
            visited_repo=visited,
            saved_routes_repo=SavedRoutesRepository(database_path),
        )

        assert summary.visited_count == 1
        assert summary.progress_percent == round(100 / len(catalog.places))
        assert summary.achievement_labels == ("🏅 Первое открытие",)

    asyncio.run(scenario())


def test_profile_awards_route_explorer_after_three_completed_routes(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        completed = CompletedRoutesRepository(database_path)
        for index in range(3):
            route = SavedRoute(
                route_id=f"route-{index}",
                city_slug=CITY_SLUG,
                interest="classic",
                budget_minutes=120,
                place_slugs=("palace-square",),
                created_at="2026-10-01 00:00:00",
            )
            await completed.add(77, CITY_SLUG, route.route_id)
            await completed.add_snapshot(77, route)

        summary = await build_profile_summary(
            77,
            get_catalog(CITY_SLUG),
            dismissed_repo=DismissedRepository(database_path),
            favorites_repo=FavoritesRepository(database_path),
            interests_repo=InterestsRepository(database_path),
            visited_repo=VisitedRepository(database_path),
            saved_routes_repo=SavedRoutesRepository(database_path),
            completed_routes_repo=completed,
        )

        assert "🏁 Первый маршрут" in summary.achievement_labels
        assert "🥾 Маршрутный исследователь" in summary.achievement_labels

    asyncio.run(scenario())


def test_profile_ignores_legacy_completion_marker_without_snapshot(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        completed = CompletedRoutesRepository(database_path)
        await completed.add(88, CITY_SLUG, "legacy-marker")

        summary = await build_profile_summary(
            88,
            get_catalog(CITY_SLUG),
            dismissed_repo=DismissedRepository(database_path),
            favorites_repo=FavoritesRepository(database_path),
            interests_repo=InterestsRepository(database_path),
            visited_repo=VisitedRepository(database_path),
            saved_routes_repo=SavedRoutesRepository(database_path),
            completed_routes_repo=completed,
        )

        assert summary.completed_routes_count == 0
        assert "🏁 Первый маршрут" not in summary.achievement_labels

    asyncio.run(scenario())

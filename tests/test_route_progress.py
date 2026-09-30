import asyncio

import pytest

from app.catalog import get_catalog
from app.data.spb import CITY_SLUG
from app.database import migrate_database
from app.route_progress import mark_saved_route_visited
from app.saved_routes import SavedRoute
from app.storage import VisitedRepository


def route(*place_slugs: str, city_slug: str = CITY_SLUG) -> SavedRoute:
    return SavedRoute(
        route_id="route123",
        city_slug=city_slug,
        interest="classic",
        budget_minutes=240,
        place_slugs=tuple(place_slugs),
        created_at="2026-09-30 12:00:00",
    )


def test_route_completion_marks_available_unique_places_and_skips_stale(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        visited = VisitedRepository(database_path)
        await visited.add(42, CITY_SLUG, "hermitage")

        result = await mark_saved_route_visited(
            42,
            get_catalog(CITY_SLUG),
            route(
                "hermitage",
                "missing-place",
                "hermitage",
                "summer-garden",
            ),
            visited,
        )

        assert result.added_count == 1
        assert result.already_visited_count == 1
        assert result.unavailable_count == 1
        assert result.available_count == 2
        assert set(await visited.list_place_slugs(42, CITY_SLUG)) == {
            "hermitage",
            "summer-garden",
        }

    asyncio.run(scenario())


def test_route_completion_is_idempotent(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        visited = VisitedRepository(database_path)
        saved = route("hermitage", "summer-garden")

        first = await mark_saved_route_visited(
            7,
            get_catalog(CITY_SLUG),
            saved,
            visited,
        )
        second = await mark_saved_route_visited(
            7,
            get_catalog(CITY_SLUG),
            saved,
            visited,
        )

        assert first.added_count == 2
        assert first.already_visited_count == 0
        assert second.added_count == 0
        assert second.already_visited_count == 2

    asyncio.run(scenario())


def test_route_completion_is_user_scoped(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        visited = VisitedRepository(database_path)

        await mark_saved_route_visited(
            1,
            get_catalog(CITY_SLUG),
            route("hermitage"),
            visited,
        )

        assert await visited.list_place_slugs(1, CITY_SLUG) == ("hermitage",)
        assert await visited.list_place_slugs(2, CITY_SLUG) == ()

    asyncio.run(scenario())


def test_route_completion_rejects_different_city_catalog(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        visited = VisitedRepository(database_path)

        with pytest.raises(ValueError, match="city"):
            await mark_saved_route_visited(
                1,
                get_catalog(CITY_SLUG),
                route("hermitage", city_slug="perm"),
                visited,
            )

        assert await visited.list_place_slugs(1, CITY_SLUG) == ()

    asyncio.run(scenario())

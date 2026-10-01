import asyncio

from app.catalog import get_catalog
from app.route_completion import RouteCompletionResult, complete_saved_route
from app.storage import CompletedRoutesRepository, SavedRoutesRepository, VisitedRepository

CITY_SLUG = "saint-petersburg"


def test_route_completion_result_shape() -> None:
    result = RouteCompletionResult(
        added=1,
        already_visited=2,
        unavailable=3,
    )

    assert result.added == 1
    assert result.already_visited == 2
    assert result.unavailable == 3


def test_complete_saved_route_marks_available_places_and_skips_stale(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "bot.sqlite3")
        saved_routes = SavedRoutesRepository(database_path)
        visited = VisitedRepository(database_path)
        await saved_routes.initialize()
        catalog = get_catalog(CITY_SLUG)
        first, second = catalog.places[:2]

        saved = await saved_routes.save(
            101,
            CITY_SLUG,
            "classic",
            120,
            (first.slug, "removed-place", second.slug),
        )
        await visited.add(101, CITY_SLUG, first.slug)

        result = await complete_saved_route(
            user_id=101,
            city_slug=CITY_SLUG,
            route_id=saved.route_id,
            saved_routes=saved_routes,
            visited=visited,
            catalog=catalog,
        )

        assert result == RouteCompletionResult(
            added=1,
            already_visited=1,
            unavailable=1,
        )
        assert await visited.contains(101, CITY_SLUG, first.slug)
        assert await visited.contains(101, CITY_SLUG, second.slug)

    asyncio.run(scenario())


def test_complete_saved_route_is_idempotent(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "bot.sqlite3")
        saved_routes = SavedRoutesRepository(database_path)
        visited = VisitedRepository(database_path)
        completed = CompletedRoutesRepository(database_path)
        await saved_routes.initialize()
        catalog = get_catalog(CITY_SLUG)
        slugs = tuple(place.slug for place in catalog.places[:2])
        saved = await saved_routes.save(202, CITY_SLUG, "classic", 120, slugs)

        first = await complete_saved_route(
            user_id=202,
            city_slug=CITY_SLUG,
            route_id=saved.route_id,
            saved_routes=saved_routes,
            visited=visited,
            catalog=catalog,
            completed_routes=completed,
        )
        second = await complete_saved_route(
            user_id=202,
            city_slug=CITY_SLUG,
            route_id=saved.route_id,
            saved_routes=saved_routes,
            visited=visited,
            catalog=catalog,
            completed_routes=completed,
        )

        assert first == RouteCompletionResult(added=2, already_visited=0, unavailable=0)
        assert second == RouteCompletionResult(added=0, already_visited=2, unavailable=0)
        assert set(await visited.list_place_slugs(202, CITY_SLUG)) == set(slugs)
        assert await completed.contains(202, CITY_SLUG, saved.route_id)
        assert await completed.count(202, CITY_SLUG) == 1

    asyncio.run(scenario())


def test_complete_saved_route_rejects_other_user_and_city(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "bot.sqlite3")
        saved_routes = SavedRoutesRepository(database_path)
        visited = VisitedRepository(database_path)
        await saved_routes.initialize()
        catalog = get_catalog(CITY_SLUG)
        slug = catalog.places[0].slug
        saved = await saved_routes.save(303, CITY_SLUG, "classic", 120, (slug,))

        other_user = await complete_saved_route(
            user_id=404,
            city_slug=CITY_SLUG,
            route_id=saved.route_id,
            saved_routes=saved_routes,
            visited=visited,
            catalog=catalog,
        )
        other_city = await complete_saved_route(
            user_id=303,
            city_slug="perm",
            route_id=saved.route_id,
            saved_routes=saved_routes,
            visited=visited,
            catalog=get_catalog("perm"),
        )

        assert other_user is None
        assert other_city is None
        assert not await visited.contains(303, CITY_SLUG, slug)
        assert not await visited.contains(404, CITY_SLUG, slug)

    asyncio.run(scenario())

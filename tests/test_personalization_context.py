import asyncio

from app.data.spb import CITY_SLUG
from app.personalization_context import load_personalization_context
from app.saved_routes import route_id_for
from app.saved_routes import SavedRoute
from app.storage import (
    CompletedRoutesRepository,
    DismissedRepository,
    FavoritesRepository,
    InterestsRepository,
    VisitedRepository,
    migrate_database,
)


def test_personalization_context_is_city_and_user_scoped(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        dismissed = DismissedRepository(database_path)
        favorites = FavoritesRepository(database_path)
        interests = InterestsRepository(database_path)
        visited = VisitedRepository(database_path)
        completed = CompletedRoutesRepository(database_path)

        await interests.add(1, CITY_SLUG, "museums")
        await favorites.add(1, CITY_SLUG, "russian-museum")
        await visited.add(1, CITY_SLUG, "hermitage")
        await dismissed.add(1, CITY_SLUG, "faberge-museum")
        route = SavedRoute(
                route_id=route_id_for(
                    CITY_SLUG,
                    "museums",
                    240,
                    ("erarta", "removed-place"),
                ),
                city_slug=CITY_SLUG,
                interest="museums",
                budget_minutes=240,
                place_slugs=("erarta", "removed-place"),
                created_at="2026-10-01 00:00:00",
            )
        await completed.complete_route(1, route, set())

        await interests.add(2, CITY_SLUG, "walks")
        await favorites.add(1, "other-city", "foreign-place")

        context = await load_personalization_context(
            1,
            CITY_SLUG,
            dismissed_repo=dismissed,
            favorites_repo=favorites,
            interests_repo=interests,
            visited_repo=visited,
            completed_routes_repo=completed,
        )

        assert context.interests == ("museums",)
        assert context.favorite_slugs == frozenset({"russian-museum"})
        assert context.visited_slugs == frozenset({"hermitage"})
        assert context.dismissed_slugs == frozenset({"faberge-museum"})
        assert context.completed_route_place_slugs == frozenset(
            {"erarta", "removed-place"}
        )
        assert context.excluded_slugs == frozenset(
            {"hermitage", "faberge-museum", "erarta", "removed-place"}
        )

    asyncio.run(scenario())


def test_personalization_context_empty_state(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        context = await load_personalization_context(
            99,
            CITY_SLUG,
            dismissed_repo=DismissedRepository(database_path),
            favorites_repo=FavoritesRepository(database_path),
            interests_repo=InterestsRepository(database_path),
            visited_repo=VisitedRepository(database_path),
            completed_routes_repo=CompletedRoutesRepository(database_path),
        )

        assert context.interests == ()
        assert context.favorite_slugs == frozenset()
        assert context.visited_slugs == frozenset()
        assert context.dismissed_slugs == frozenset()
        assert context.completed_route_place_slugs == frozenset()
        assert context.excluded_slugs == frozenset()

    asyncio.run(scenario())

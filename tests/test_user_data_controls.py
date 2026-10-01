import asyncio

import pytest

from app.data.spb import CITY_SLUG
from app.database import migrate_database
from app.storage import (
    CompletedRoutesRepository,
    DismissedRepository,
    FavoritesRepository,
    InterestsRepository,
    SavedRoutesRepository,
    UserCityRepository,
    VisitedRepository,
)
from app.user_data_controls import (
    UserDataControlsRepository,
    bound_city_slug,
)


def test_delete_city_data_is_scoped_transactional_and_preserves_city_preference(
    tmp_path,
) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)

        dismissed = DismissedRepository(database_path)
        favorites = FavoritesRepository(database_path)
        interests = InterestsRepository(database_path)
        visited = VisitedRepository(database_path)
        saved_routes = SavedRoutesRepository(database_path)
        city_preferences = UserCityRepository(database_path)
        controls = UserDataControlsRepository(database_path)
        completed_routes = CompletedRoutesRepository(database_path)

        await city_preferences.set_city_slug(1, CITY_SLUG)

        await dismissed.add(1, CITY_SLUG, "new-holland")
        await favorites.add(1, CITY_SLUG, "hermitage")
        await interests.add(1, CITY_SLUG, "museums")
        await visited.add(1, CITY_SLUG, "summer-garden")
        own_route = await saved_routes.save(
            1,
            CITY_SLUG,
            "classic",
            240,
            ("palace-square", "hermitage"),
        )
        await completed_routes.complete_route(
            1, own_route, {"palace-square", "hermitage"}
        )

        await dismissed.add(1, "another-city", "other-place")
        await favorites.add(1, "another-city", "other-place")
        await interests.add(1, "another-city", "free")
        await visited.add(1, "another-city", "other-place")
        other_city_route = await saved_routes.save(
            1,
            "another-city",
            "free",
            120,
            ("other-place",),
        )
        await completed_routes.complete_route(1, other_city_route, {"other-place"})

        await dismissed.add(2, CITY_SLUG, "summer-garden")
        await favorites.add(2, CITY_SLUG, "palace-square")
        await interests.add(2, CITY_SLUG, "walks")
        await visited.add(2, CITY_SLUG, "hermitage")
        other_user_route = await saved_routes.save(
            2,
            CITY_SLUG,
            "museums",
            120,
            ("russian-museum",),
        )
        await completed_routes.complete_route(
            2, other_user_route, {"russian-museum"}
        )

        result = await controls.delete_city_data(1, CITY_SLUG)

        assert result.dismissed == 1
        assert result.favorites == 1
        assert result.interests == 1
        assert result.visited == 1
        assert result.saved_routes == 1
        assert result.completed_routes == 1
        assert result.total == 6

        assert await dismissed.list_place_slugs(1, CITY_SLUG) == ()
        assert await favorites.list_place_slugs(1, CITY_SLUG) == ()
        assert await interests.list_interests(1, CITY_SLUG) == ()
        assert await visited.list_place_slugs(1, CITY_SLUG) == ()
        assert await saved_routes.get(1, CITY_SLUG, own_route.route_id) is None
        assert await completed_routes.count(1, CITY_SLUG) == 0

        assert await city_preferences.get_city_slug(1) == CITY_SLUG
        assert await completed_routes.count(1, "another-city") == 1
        assert await completed_routes.count(2, CITY_SLUG) == 1

        assert await dismissed.list_place_slugs(1, "another-city") == (
            "other-place",
        )
        assert await favorites.list_place_slugs(1, "another-city") == (
            "other-place",
        )
        assert await interests.list_interests(1, "another-city") == ("free",)
        assert await visited.list_place_slugs(1, "another-city") == (
            "other-place",
        )
        assert (
            await saved_routes.get(
                1,
                "another-city",
                other_city_route.route_id,
            )
            is not None
        )

        assert await dismissed.list_place_slugs(2, CITY_SLUG) == (
            "summer-garden",
        )
        assert await favorites.list_place_slugs(2, CITY_SLUG) == (
            "palace-square",
        )
        assert await interests.list_interests(2, CITY_SLUG) == ("walks",)
        assert await visited.list_place_slugs(2, CITY_SLUG) == ("hermitage",)
        assert (
            await saved_routes.get(
                2,
                CITY_SLUG,
                other_user_route.route_id,
            )
            is not None
        )

        repeated = await controls.delete_city_data(1, CITY_SLUG)
        assert repeated.total == 0

    asyncio.run(scenario())


def test_bound_city_callback_accepts_exact_active_city() -> None:
    assert bound_city_slug(
        "profile:data:delete:saint-petersburg",
        prefix="profile:data:delete:",
        current_city_slug="saint-petersburg",
    ) == "saint-petersburg"


def test_bound_city_callback_rejects_stale_city() -> None:
    with pytest.raises(ValueError, match="no longer active"):
        bound_city_slug(
            "profile:data:delete:saint-petersburg",
            prefix="profile:data:delete:",
            current_city_slug="moscow",
        )


def test_bound_city_callback_rejects_missing_city() -> None:
    with pytest.raises(ValueError, match="missing"):
        bound_city_slug(
            "profile:data:delete:",
            prefix="profile:data:delete:",
            current_city_slug=CITY_SLUG,
        )

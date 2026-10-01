import asyncio
import sqlite3

import aiosqlite
import pytest

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
    assert result.already_completed is False


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
        assert second == RouteCompletionResult(
            added=0,
            already_visited=0,
            unavailable=0,
            already_completed=True,
        )
        assert set(await visited.list_place_slugs(202, CITY_SLUG)) == set(slugs)
        assert await completed.contains(202, CITY_SLUG, saved.route_id)
        assert await completed.count(202, CITY_SLUG) == 1

        snapshots = await completed.list_snapshots(202, CITY_SLUG)
        assert len(snapshots) == 1
        assert snapshots[0].route_id == saved.route_id
        assert snapshots[0].interest == "classic"
        assert snapshots[0].budget_minutes == 120
        assert snapshots[0].place_slugs == slugs

        await saved_routes.remove(202, CITY_SLUG, saved.route_id)
        persisted = await completed.get_snapshot(202, CITY_SLUG, saved.route_id)
        assert persisted is not None
        assert persisted.place_slugs == slugs

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


def test_atomic_completion_rolls_back_visited_and_marker_on_snapshot_failure(
    tmp_path,
) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "bot.sqlite3")
        saved_routes = SavedRoutesRepository(database_path)
        visited = VisitedRepository(database_path)
        completed = CompletedRoutesRepository(database_path)
        await saved_routes.initialize()
        catalog = get_catalog(CITY_SLUG)
        slugs = tuple(place.slug for place in catalog.places[:2])
        saved = await saved_routes.save(
            505,
            CITY_SLUG,
            "classic",
            120,
            slugs,
        )

        with sqlite3.connect(database_path) as database:
            database.execute(
                """
                CREATE TRIGGER fail_completed_snapshot
                BEFORE INSERT ON completed_route_snapshots
                BEGIN
                    SELECT RAISE(ABORT, 'snapshot failure');
                END
                """
            )
            database.commit()

        with pytest.raises(aiosqlite.IntegrityError, match="snapshot failure"):
            await complete_saved_route(
                user_id=505,
                city_slug=CITY_SLUG,
                route_id=saved.route_id,
                saved_routes=saved_routes,
                visited=visited,
                catalog=catalog,
                completed_routes=completed,
            )

        assert await visited.list_place_slugs(505, CITY_SLUG) == ()
        assert not await completed.contains(505, CITY_SLUG, saved.route_id)
        assert await completed.get_snapshot(505, CITY_SLUG, saved.route_id) is None

    asyncio.run(scenario())


def test_completed_snapshot_fails_closed_on_corrupt_persisted_payload(
    tmp_path,
) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "bot.sqlite3")
        completed = CompletedRoutesRepository(database_path)
        await completed.initialize()

        with sqlite3.connect(database_path) as database:
            database.execute(
                """
                INSERT INTO completed_route_snapshots (
                    user_id,
                    city_slug,
                    route_id,
                    interest,
                    budget_minutes,
                    place_slugs_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    606,
                    CITY_SLUG,
                    "corrupt-completed",
                    "classic",
                    120,
                    '["hermitage","hermitage"]',
                ),
            )
            database.commit()

        with pytest.raises(RuntimeError, match="invalid place payload"):
            await completed.list_snapshots(606, CITY_SLUG)

    asyncio.run(scenario())


def test_completed_snapshot_rejects_route_id_tampering(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "bot.sqlite3")
        saved_routes = SavedRoutesRepository(database_path)
        completed = CompletedRoutesRepository(database_path)
        await saved_routes.initialize()
        catalog = get_catalog(CITY_SLUG)
        slugs = tuple(place.slug for place in catalog.places[:2])
        saved = await saved_routes.save(707, CITY_SLUG, "classic", 120, slugs)
        await completed.complete_route(707, saved, set(slugs))

        with sqlite3.connect(database_path) as database:
            database.execute(
                """
                UPDATE completed_route_snapshots
                SET route_id = 'tampered-route-id'
                WHERE user_id = ? AND city_slug = ? AND route_id = ?
                """,
                (707, CITY_SLUG, saved.route_id),
            )
            database.commit()

        with pytest.raises(RuntimeError, match="id does not match"):
            await completed.list_snapshots(707, CITY_SLUG)

    asyncio.run(scenario())

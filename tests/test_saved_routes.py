import asyncio
import sqlite3
from dataclasses import replace

import pytest

from app.catalog import get_catalog
from app.data.spb import CITY_SLUG
from app.database import migrate_database
from app.place_route import build_place_route
from app.planner import build_ranked_route, build_route
from app.saved_routes import (
    PERSONAL_ROUTE_INTEREST,
    PERSONAL_ROUTE_LABEL,
    PLACE_ROUTE_INTEREST,
    PLACE_ROUTE_LABEL,
    build_save_callback,
    parse_save_callback,
    route_interest_label,
)
from app.storage import SavedRoutesRepository


def test_generated_route_snapshot_round_trip_and_callback_limit() -> None:
    catalog = get_catalog(CITY_SLUG)
    route = build_route(catalog, budget_minutes=240, interest="classic")

    assert route is not None
    callback = build_save_callback(catalog, route)
    snapshot = parse_save_callback(callback, catalog)

    assert len(callback.encode("utf-8")) <= 64
    assert snapshot.interest == route.interest
    assert snapshot.budget_minutes == route.budget_minutes
    assert tuple(place.slug for place in snapshot.places) == tuple(
        place.slug for place in route.places
    )


def test_generated_route_snapshot_fails_closed_after_catalog_reorder() -> None:
    catalog = get_catalog(CITY_SLUG)
    route = build_route(catalog, budget_minutes=240, interest="classic")

    assert route is not None
    callback = build_save_callback(catalog, route)
    reordered = replace(
        catalog,
        places=tuple(reversed(catalog.places)),
    )

    with pytest.raises(ValueError, match="checksum"):
        parse_save_callback(callback, reordered)


def test_saved_routes_persist_order_and_are_idempotent(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        repository = SavedRoutesRepository(database_path)
        slugs = ("palace-square", "hermitage", "summer-garden")

        first = await repository.save(
            42,
            CITY_SLUG,
            "classic",
            240,
            slugs,
        )
        second = await repository.save(
            42,
            CITY_SLUG,
            "classic",
            240,
            slugs,
        )

        assert first.route_id == second.route_id
        assert first.place_slugs == slugs
        assert await repository.list_routes(42, CITY_SLUG) == (first,)

        loaded = await repository.get(42, CITY_SLUG, first.route_id)
        assert loaded is not None
        assert loaded.place_slugs == slugs

    asyncio.run(scenario())


def test_saved_routes_are_scoped_by_user_and_city(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        repository = SavedRoutesRepository(database_path)

        own = await repository.save(
            1,
            CITY_SLUG,
            "museums",
            120,
            ("hermitage",),
        )
        await repository.save(
            2,
            CITY_SLUG,
            "museums",
            120,
            ("russian-museum",),
        )
        await repository.save(
            1,
            "another-city",
            "free",
            120,
            ("other-place",),
        )

        assert await repository.get(2, CITY_SLUG, own.route_id) is None
        assert await repository.get(1, "another-city", own.route_id) is None

        routes = await repository.list_routes(1, CITY_SLUG)
        assert len(routes) == 1
        assert routes[0].route_id == own.route_id

    asyncio.run(scenario())


def test_saved_route_remove_is_scoped(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        repository = SavedRoutesRepository(database_path)

        route = await repository.save(
            1,
            CITY_SLUG,
            "walks",
            120,
            ("summer-garden",),
        )
        await repository.remove(2, CITY_SLUG, route.route_id)
        assert await repository.get(1, CITY_SLUG, route.route_id) is not None

        await repository.remove(1, CITY_SLUG, route.route_id)
        assert await repository.get(1, CITY_SLUG, route.route_id) is None

    asyncio.run(scenario())



def test_personal_route_snapshot_round_trip() -> None:
    catalog = get_catalog(CITY_SLUG)
    route = build_ranked_route(
        catalog.places[:6],
        budget_minutes=240,
        route_interest=PERSONAL_ROUTE_INTEREST,
    )

    assert route is not None
    callback = build_save_callback(catalog, route)
    snapshot = parse_save_callback(callback, catalog)

    assert snapshot.interest == PERSONAL_ROUTE_INTEREST
    assert snapshot.budget_minutes == 240
    assert tuple(place.slug for place in snapshot.places) == tuple(
        place.slug for place in route.places
    )
    assert route_interest_label(PERSONAL_ROUTE_INTEREST) == PERSONAL_ROUTE_LABEL



def test_place_route_snapshot_round_trip() -> None:
    catalog = get_catalog(CITY_SLUG)
    route = build_place_route(
        catalog,
        "hermitage",
        budget_minutes=240,
    )

    assert route is not None
    callback = build_save_callback(catalog, route)
    snapshot = parse_save_callback(callback, catalog)

    assert snapshot.interest == PLACE_ROUTE_INTEREST
    assert snapshot.budget_minutes == 240
    assert snapshot.places[0].slug == "hermitage"
    assert tuple(place.slug for place in snapshot.places) == tuple(
        place.slug for place in route.places
    )
    assert route_interest_label(PLACE_ROUTE_INTEREST) == PLACE_ROUTE_LABEL


def test_saved_route_rejects_duplicate_places_and_nonpositive_budget(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        repository = SavedRoutesRepository(database_path)

        with pytest.raises(ValueError, match="unique"):
            await repository.save(
                42,
                CITY_SLUG,
                "classic",
                120,
                ("hermitage", "hermitage"),
            )
        with pytest.raises(ValueError, match="positive"):
            await repository.save(
                42,
                CITY_SLUG,
                "classic",
                0,
                ("hermitage",),
            )

        assert await repository.list_routes(42, CITY_SLUG) == ()

    asyncio.run(scenario())


def test_saved_route_fails_closed_on_corrupt_persisted_payload(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        repository = SavedRoutesRepository(database_path)

        with sqlite3.connect(database_path) as database:
            database.execute(
                """
                INSERT INTO saved_routes (
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
                    42,
                    CITY_SLUG,
                    "corrupt-route",
                    "classic",
                    120,
                    '["hermitage","hermitage"]',
                ),
            )
            database.commit()

        with pytest.raises(RuntimeError, match="invalid place payload"):
            await repository.get(42, CITY_SLUG, "corrupt-route")

    asyncio.run(scenario())

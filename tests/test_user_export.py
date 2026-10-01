import asyncio
import json

import pytest

from app.catalog import get_catalog
from app.data.spb import CITY_SLUG
from app.database import migrate_database
from app.storage import (
    CompletedRoutesRepository,
    DismissedRepository,
    FavoritesRepository,
    InterestsRepository,
    SavedRoutesRepository,
    UserCityRepository,\n    VisitedRepository,\n)
from app.user_export import (
    EXPORT_SCHEMA_VERSION,
    account_export_filename,
    build_account_export,
    build_user_export,
    export_filename,
    serialize_user_export,
)


def test_export_is_user_and_city_scoped_and_preserves_route_order(tmp_path) -> None:
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
        await dismissed.add(1, CITY_SLUG, "stale-dismissed")
        await dismissed.add(1, "another-city", "other-place")
        await dismissed.add(2, CITY_SLUG, "palace-square")

        await favorites.add(1, CITY_SLUG, "hermitage")
        await favorites.add(1, CITY_SLUG, "stale-place")
        await favorites.add(1, "another-city", "other-place")
        await favorites.add(2, CITY_SLUG, "palace-square")

        await interests.add(1, CITY_SLUG, "museums")
        await interests.add(1, "another-city", "free")
        await interests.add(2, CITY_SLUG, "walks")

        await visited.add(1, CITY_SLUG, "summer-garden")
        await visited.add(2, CITY_SLUG, "hermitage")

        route = await saved_routes.save(
            1,
            CITY_SLUG,
            "classic",
            240,
            ("palace-square", "hermitage", "summer-garden"),
        )
        await saved_routes.save(
            1,
            "another-city",
            "free",
            120,
            ("other-place",),
        )
        await saved_routes.save(
            2,
            CITY_SLUG,
            "museums",
            120,
            ("russian-museum",),
        )

        await completed_routes.complete_route(
            1,
            route,
            set(),
        )

        data = await build_user_export(
            1,
            get_catalog(CITY_SLUG),
            dismissed_repo=dismissed,
            favorites_repo=favorites,
            interests_repo=interests,
            visited_repo=visited,
            saved_routes_repo=saved_routes,
            completed_routes_repo=completed_routes,
        )

        assert data["schema_version"] == EXPORT_SCHEMA_VERSION
        assert data["city"] == {
            "slug": CITY_SLUG,
            "name": "Санкт-Петербург",
        }
        assert data["interests"] == [
            {"id": "museums", "label": "🖼 Музеи"}
        ]

        dismissed_by_slug = {
            item["place_slug"]: item
            for item in data["dismissed"]
        }
        assert dismissed_by_slug["new-holland"]["title"] == "Новая Голландия"
        assert dismissed_by_slug["stale-dismissed"]["title"] is None
        assert "other-place" not in dismissed_by_slug
        assert "palace-square" not in dismissed_by_slug

        favorites_by_slug = {
            item["place_slug"]: item
            for item in data["favorites"]
        }
        assert favorites_by_slug["hermitage"]["title"] == "Государственный Эрмитаж"
        assert favorites_by_slug["stale-place"]["title"] is None
        assert "other-place" not in favorites_by_slug
        assert "palace-square" not in favorites_by_slug

        assert data["visited"] == [
            {
                "place_slug": "summer-garden",
                "title": "Летний сад",
            }
        ]

        assert len(data["completed_routes"]) == 1
        completed = data["completed_routes"][0]
        assert completed["route_id"] == route.route_id
        assert completed["budget_minutes"] == 240
        assert [stop["place_slug"] for stop in completed["stops"]] == [
            "palace-square",
            "hermitage",
            "summer-garden",
        ]
        assert len(data["saved_routes"]) == 1
        exported_route = data["saved_routes"][0]
        assert exported_route["route_id"] == route.route_id
        assert exported_route["budget_minutes"] == 240
        assert [stop["place_slug"] for stop in exported_route["stops"]] == [
            "palace-square",
            "hermitage",
            "summer-garden",
        ]

    asyncio.run(scenario())


def test_serialized_export_is_utf8_deterministic_and_has_no_location_data(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        catalog = get_catalog(CITY_SLUG)

        data = await build_user_export(
            99,
            catalog,
            dismissed_repo=DismissedRepository(database_path),
            favorites_repo=FavoritesRepository(database_path),
            interests_repo=InterestsRepository(database_path),
            visited_repo=VisitedRepository(database_path),
            saved_routes_repo=SavedRoutesRepository(database_path),
            completed_routes_repo=CompletedRoutesRepository(database_path),
        )

        first = serialize_user_export(data)
        second = serialize_user_export(data)

        assert first == second
        assert first.endswith(b"\n")
        decoded = first.decode("utf-8")
        parsed = json.loads(decoded)
        assert parsed == data

        lowered = decoded.casefold()
        assert "latitude" not in lowered
        assert "longitude" not in lowered
        assert "location" not in lowered
        assert "user_id" not in lowered
        assert "bot_token" not in lowered

        assert export_filename(catalog) == "places-saint-petersburg.json"

    asyncio.run(scenario())


def test_export_rejects_repositories_from_different_databases(tmp_path) -> None:
    async def scenario() -> None:
        first = str(tmp_path / "first.db")
        second = str(tmp_path / "second.db")
        await migrate_database(first)
        await migrate_database(second)

        with pytest.raises(ValueError, match="same database"):
            await build_user_export(
                1,
                get_catalog(CITY_SLUG),
                dismissed_repo=DismissedRepository(first),
                favorites_repo=FavoritesRepository(second),
                interests_repo=InterestsRepository(first),
                visited_repo=VisitedRepository(first),
                saved_routes_repo=SavedRoutesRepository(first),
                completed_routes_repo=CompletedRoutesRepository(first),
            )

    asyncio.run(scenario())


def test_account_export_contains_all_user_cities_without_private_identifiers(
    tmp_path,
) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        favorites = FavoritesRepository(database_path)\n        interests = InterestsRepository(database_path)\n        city_preferences = UserCityRepository(database_path)\n\n        await city_preferences.set_city_slug(1, "moscow")\n        await favorites.add(1, CITY_SLUG, "hermitage")
        await favorites.add(1, "moscow", "red-square")
        await interests.add(1, "legacy-city", "walks")
        await favorites.add(2, "moscow", "red-square")

        data = await build_account_export(1, database_path=database_path)

        assert data["scope"] == "account"\n        assert data["selected_city"] == {"slug": "moscow", "name": "Москва"}\n        assert [city["city"]["slug"] for city in data["cities"]] == [
            "legacy-city",
            "moscow",
            CITY_SLUG,
        ]
        legacy = data["cities"][0]
        assert legacy["city"]["name"] is None
        assert legacy["interests"] == [{"id": "walks", "label": "🌿 Прогулки"}]

        encoded = serialize_user_export(data).decode("utf-8").casefold()
        assert "user_id" not in encoded
        assert "latitude" not in encoded
        assert "longitude" not in encoded
        assert "bot_token" not in encoded
        assert account_export_filename() == "places-all-cities.json"

    asyncio.run(scenario())


def test_account_export_includes_preference_when_no_city_scoped_data(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        preferences = UserCityRepository(database_path)
        await preferences.set_city_slug(77, "legacy-city")

        data = await build_account_export(77, database_path=database_path)

        assert data["schema_version"] == EXPORT_SCHEMA_VERSION
        assert data["scope"] == "account"
        assert data["selected_city"] == {
            "slug": "legacy-city",
            "name": None,
        }
        assert data["cities"] == []

    asyncio.run(scenario())

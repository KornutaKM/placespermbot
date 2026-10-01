from __future__ import annotations

import json
from typing import Any

from app.catalog import CityCatalog, get_catalog, has_catalog
from app.planner import INTEREST_LABELS
from app.storage import (
    CompletedRoutesRepository,
    DismissedRepository,
    FavoritesRepository,
    InterestsRepository,
    SavedRoutesRepository,
    UserDataSnapshotRepository,
    VisitedRepository,
)

EXPORT_SCHEMA_VERSION = 5


async def build_user_export(
    user_id: int,
    catalog: CityCatalog,
    *,
    dismissed_repo: DismissedRepository,
    favorites_repo: FavoritesRepository,
    interests_repo: InterestsRepository,
    visited_repo: VisitedRepository,
    saved_routes_repo: SavedRoutesRepository,
    completed_routes_repo: CompletedRoutesRepository,
) -> dict[str, Any]:
    repositories = (
        dismissed_repo,
        favorites_repo,
        interests_repo,
        visited_repo,
        saved_routes_repo,
        completed_routes_repo,
    )
    database_paths = {repo.database_path.resolve() for repo in repositories}
    if len(database_paths) != 1:
        raise ValueError("User export repositories must use the same database")

    snapshot = await UserDataSnapshotRepository(database_paths.pop()).load(
        user_id,
        catalog.slug,
    )
    interests = snapshot.interests
    dismissed_slugs = snapshot.dismissed_slugs
    favorite_slugs = snapshot.favorite_slugs
    visited_slugs = snapshot.visited_slugs
    saved_routes = snapshot.saved_routes
    completed_routes = snapshot.completed_routes

    return {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "city": {
            "slug": catalog.slug,
            "name": catalog.name,
        },
        "interests": [
            {
                "id": interest,
                "label": INTEREST_LABELS.get(interest, interest),
            }
            for interest in interests
        ],
        "dismissed": [
            _place_reference(catalog, slug)
            for slug in dismissed_slugs
        ],
        "favorites": [
            _place_reference(catalog, slug)
            for slug in favorite_slugs
        ],
        "visited": [
            _place_reference(catalog, slug)
            for slug in visited_slugs
        ],
        "completed_routes": [
            {
                "route_id": route.route_id,
                "interest": {
                    "id": route.interest,
                    "label": INTEREST_LABELS.get(route.interest, route.interest),
                },
                "budget_minutes": route.budget_minutes,
                "stops": [
                    _place_reference(catalog, slug)
                    for slug in route.place_slugs
                ],
                "completed_at": route.completed_at,
            }
            for route in completed_routes
        ],
        "saved_routes": [
            {
                "route_id": route.route_id,
                "interest": {
                    "id": route.interest,
                    "label": INTEREST_LABELS.get(route.interest, route.interest),
                },
                "budget_minutes": route.budget_minutes,
                "stops": [
                    _place_reference(catalog, slug)
                    for slug in route.place_slugs
                ],
                "created_at": route.created_at,
            }
            for route in saved_routes
        ],
    }



async def build_account_export(
    user_id: int,
    *,
    database_path: str,
) -> dict[str, Any]:
    account = await UserDataSnapshotRepository(database_path).load_account(user_id)\n    snapshots = account.cities\n    cities: list[dict[str, Any]] = []
    for city_slug, snapshot in snapshots.items():
        catalog = get_catalog(city_slug) if has_catalog(city_slug) else None

        def place_reference(
            place_slug: str,
            city_catalog: CityCatalog | None = catalog,
        ) -> dict[str, str | None]:
            if city_catalog is None:
                return {"place_slug": place_slug, "title": None}
            return _place_reference(city_catalog, place_slug)

        cities.append(
            {
                "city": {
                    "slug": city_slug,
                    "name": catalog.name if catalog is not None else None,
                },
                "interests": [
                    {
                        "id": interest,
                        "label": INTEREST_LABELS.get(interest, interest),
                    }
                    for interest in snapshot.interests
                ],
                "dismissed": [
                    place_reference(slug) for slug in snapshot.dismissed_slugs
                ],
                "favorites": [
                    place_reference(slug) for slug in snapshot.favorite_slugs
                ],
                "visited": [
                    place_reference(slug) for slug in snapshot.visited_slugs
                ],
                "completed_routes": [
                    {
                        "route_id": route.route_id,
                        "interest": {
                            "id": route.interest,
                            "label": INTEREST_LABELS.get(
                                route.interest,
                                route.interest,
                            ),
                        },
                        "budget_minutes": route.budget_minutes,
                        "stops": [
                            place_reference(slug) for slug in route.place_slugs
                        ],
                        "completed_at": route.completed_at,
                    }
                    for route in snapshot.completed_routes
                ],
                "saved_routes": [
                    {
                        "route_id": route.route_id,
                        "interest": {
                            "id": route.interest,
                            "label": INTEREST_LABELS.get(
                                route.interest,
                                route.interest,
                            ),
                        },
                        "budget_minutes": route.budget_minutes,
                        "stops": [
                            place_reference(slug) for slug in route.place_slugs
                        ],
                        "created_at": route.created_at,
                    }
                    for route in snapshot.saved_routes
                ],
            }
        )

    selected_catalog = (
        get_catalog(account.selected_city_slug)
        if account.selected_city_slug is not None
        and has_catalog(account.selected_city_slug)
        else None
    )
    selected_city = (
        {
            "slug": account.selected_city_slug,
            "name": selected_catalog.name if selected_catalog is not None else None,
        }
        if account.selected_city_slug is not None
        else None
    )

    return {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "scope": "account",
        "selected_city": selected_city,
        "cities": cities,
    }


def account_export_filename() -> str:
    return "places-all-cities.json"

def serialize_user_export(data: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def export_filename(catalog: CityCatalog) -> str:
    return f"places-{catalog.slug}.json"


def _place_reference(
    catalog: CityCatalog,
    place_slug: str,
) -> dict[str, str | None]:
    place = catalog.place_by_slug(place_slug)
    return {
        "place_slug": place_slug,
        "title": place.title if place is not None else None,
    }

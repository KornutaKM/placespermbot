from __future__ import annotations

import asyncio
import json
from typing import Any

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

EXPORT_SCHEMA_VERSION = 4


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
        completed_routes_repo.list_snapshots(user_id, catalog.slug),
    )

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

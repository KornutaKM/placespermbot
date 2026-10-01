from __future__ import annotations

from collections.abc import Collection

from app.catalog import CityCatalog
from app.domain import GeneratedRoute
from app.planner import build_ranked_route
from app.recommendations import recommend_personalized
from app.saved_routes import PERSONAL_ROUTE_INTEREST


def build_personal_route(
    catalog: CityCatalog,
    interests: tuple[str, ...],
    *,
    budget_minutes: int,
    favorite_slugs: Collection[str] = (),
    visited_slugs: Collection[str] = (),
    completed_route_place_slugs: Collection[str] = (),
    dismissed_slugs: Collection[str] = (),
    start_latitude: float | None = None,
    start_longitude: float | None = None,
) -> GeneratedRoute | None:
    excluded = (
        set(visited_slugs)
        | set(completed_route_place_slugs)
        | set(dismissed_slugs)
    )
    recommendations = recommend_personalized(
        catalog,
        interests,
        limit=len(catalog.places),
        favorite_slugs=favorite_slugs,
        visited_slugs=visited_slugs,
        completed_route_place_slugs=completed_route_place_slugs,
        exclude_slugs=excluded,
    )
    candidates = tuple(item.place for item in recommendations)

    return build_ranked_route(
        candidates,
        budget_minutes=budget_minutes,
        route_interest=PERSONAL_ROUTE_INTEREST,
        start_latitude=start_latitude,
        start_longitude=start_longitude,
    )

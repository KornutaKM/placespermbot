from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass

from app.catalog import CityCatalog
from app.domain import GeneratedRoute
from app.planner import build_ranked_route
from app.recommendations import PersonalRecommendation, recommend_personalized
from app.saved_routes import PERSONAL_ROUTE_INTEREST



@dataclass(frozen=True, slots=True)
class PersonalRouteResult:
    route: GeneratedRoute
    recommendations: tuple[PersonalRecommendation, ...]

    def recommendation_for(self, place_slug: str) -> PersonalRecommendation | None:
        return next(
            (item for item in self.recommendations if item.place.slug == place_slug),
            None,
        )


def build_explained_personal_route(
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
) -> PersonalRouteResult | None:
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
    route = build_ranked_route(
        tuple(item.place for item in recommendations),
        budget_minutes=budget_minutes,
        route_interest=PERSONAL_ROUTE_INTEREST,
        start_latitude=start_latitude,
        start_longitude=start_longitude,
    )
    if route is None:
        return None
    selected_slugs = {place.slug for place in route.places}
    return PersonalRouteResult(
        route=route,
        recommendations=tuple(
            item for item in recommendations if item.place.slug in selected_slugs
        ),
    )

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
    result = build_explained_personal_route(
        catalog,
        interests,
        budget_minutes=budget_minutes,
        favorite_slugs=favorite_slugs,
        visited_slugs=visited_slugs,
        completed_route_place_slugs=completed_route_place_slugs,
        dismissed_slugs=dismissed_slugs,
        start_latitude=start_latitude,
        start_longitude=start_longitude,
    )
    return result.route if result is not None else None

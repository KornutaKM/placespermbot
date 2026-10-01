from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.storage import (
    CompletedRoutesRepository,
    DismissedRepository,
    FavoritesRepository,
    InterestsRepository,
    VisitedRepository,
)


@dataclass(frozen=True, slots=True)
class PersonalizationContext:
    interests: tuple[str, ...]
    dismissed_slugs: frozenset[str]
    favorite_slugs: frozenset[str]
    visited_slugs: frozenset[str]
    completed_route_place_slugs: frozenset[str]

    @property
    def excluded_slugs(self) -> frozenset[str]:
        return (
            self.dismissed_slugs
            | self.visited_slugs
            | self.completed_route_place_slugs
        )


async def load_personalization_context(
    user_id: int,
    city_slug: str,
    *,
    dismissed_repo: DismissedRepository,
    favorites_repo: FavoritesRepository,
    interests_repo: InterestsRepository,
    visited_repo: VisitedRepository,
    completed_routes_repo: CompletedRoutesRepository,
) -> PersonalizationContext:
    (
        interests,
        dismissed_slugs,
        favorite_slugs,
        visited_slugs,
        completed_snapshots,
    ) = await asyncio.gather(
        interests_repo.list_interests(user_id, city_slug),
        dismissed_repo.list_place_slugs(user_id, city_slug),
        favorites_repo.list_place_slugs(user_id, city_slug),
        visited_repo.list_place_slugs(user_id, city_slug),
        completed_routes_repo.list_snapshots(user_id, city_slug),
    )
    completed_route_place_slugs = frozenset(
        slug
        for snapshot in completed_snapshots
        for slug in snapshot.place_slugs
    )
    return PersonalizationContext(
        interests=tuple(interests),
        dismissed_slugs=frozenset(dismissed_slugs),
        favorite_slugs=frozenset(favorite_slugs),
        visited_slugs=frozenset(visited_slugs),
        completed_route_place_slugs=completed_route_place_slugs,
    )

from __future__ import annotations

from dataclasses import dataclass

from app.catalog import CityCatalog
from app.saved_routes import SavedRoute
from app.storage import VisitedRepository


@dataclass(frozen=True, slots=True)
class RouteCompletionResult:
    added_count: int
    already_visited_count: int
    unavailable_count: int

    @property
    def available_count(self) -> int:
        return self.added_count + self.already_visited_count


async def mark_saved_route_visited(
    user_id: int,
    catalog: CityCatalog,
    route: SavedRoute,
    visited_repo: VisitedRepository,
) -> RouteCompletionResult:
    available_slugs = _available_unique_slugs(catalog, route.place_slugs)
    unavailable_count = len(set(route.place_slugs)) - len(available_slugs)

    existing = set(
        await visited_repo.list_place_slugs(user_id, catalog.slug)
    )
    new_slugs = tuple(
        slug
        for slug in available_slugs
        if slug not in existing
    )
    already_count = len(available_slugs) - len(new_slugs)

    await visited_repo.add_many(
        user_id,
        catalog.slug,
        new_slugs,
    )

    return RouteCompletionResult(
        added_count=len(new_slugs),
        already_visited_count=already_count,
        unavailable_count=unavailable_count,
    )


def _available_unique_slugs(
    catalog: CityCatalog,
    place_slugs: tuple[str, ...],
) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []

    for slug in place_slugs:
        if slug in seen:
            continue
        seen.add(slug)

        if catalog.place_by_slug(slug) is not None:
            result.append(slug)

    return tuple(result)

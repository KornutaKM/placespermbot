from __future__ import annotations

from dataclasses import dataclass

from app.catalog import CityCatalog
from app.storage import SavedRoutesRepository, VisitedRepository


@dataclass(frozen=True, slots=True)
class RouteCompletionResult:
    added: int
    already_visited: int
    unavailable: int


async def complete_saved_route(
    *,
    user_id: int,
    city_slug: str,
    route_id: str,
    saved_routes: SavedRoutesRepository,
    visited: VisitedRepository,
    catalog: CityCatalog,
) -> RouteCompletionResult | None:
    """Mark all available places from a saved route as visited.

    The operation is intentionally scoped by user and city. The route snapshot is
    trusted only after it is loaded through SavedRoutesRepository, and stale
    catalog entries are ignored instead of failing the whole operation.
    """
    route = await saved_routes.get(user_id, city_slug, route_id)
    if route is None:
        return None

    available = {place.slug for place in catalog.places}
    added = 0
    already_visited = 0
    unavailable = 0

    for place_slug in route.place_slugs:
        if place_slug not in available:
            unavailable += 1
            continue

        if await visited.contains(user_id, city_slug, place_slug):
            already_visited += 1
            continue

        await visited.add(user_id, city_slug, place_slug)
        added += 1

    return RouteCompletionResult(
        added=added,
        already_visited=already_visited,
        unavailable=unavailable,
    )

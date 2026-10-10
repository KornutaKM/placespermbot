"""Signed-user dashboard snapshots assembled from existing SQLite repositories."""

from __future__ import annotations

from app.catalog import CityCatalog
from app.maps import google_maps_route_links
from app.saved_routes import SavedRoute, route_interest_label
from app.storage import (
    CompletedRoutesRepository,
    FavoritesRepository,
    SavedRoutesRepository,
    VisitedRepository,
)


def _route_view(route: SavedRoute, catalog: CityCatalog, *, completed: bool) -> dict:
    visible = tuple(
        place
        for slug in route.place_slugs
        if (place := catalog.place_by_slug(slug)) is not None
    )
    return {
        "route_id": route.route_id,
        "interest_label": route_interest_label(route.interest),
        "budget_minutes": route.budget_minutes,
        "created_at": route.created_at,
        "place_count": len(route.place_slugs),
        "unavailable_count": len(route.place_slugs) - len(visible),
        "places": [
            {"slug": place.slug, "title": place.title, "emoji": place.emoji}
            for place in visible
        ],
        "map_links": [
            {"url": link.url, "mode": link.mode}
            for link in google_maps_route_links(visible)
        ],
        "completed": completed,
    }


async def my_guide_snapshot(
    user_id: int,
    catalog: CityCatalog,
    *,
    favorites: FavoritesRepository,
    visited: VisitedRepository,
    saved_routes: SavedRoutesRepository,
    completed_routes: CompletedRoutesRepository,
) -> dict:
    """Read-only profile. Missing catalog entries are not deleted from SQLite."""
    slug = catalog.slug
    favorite_slugs = await favorites.list_place_slugs(user_id, slug)
    visited_slugs = await visited.list_place_slugs(user_id, slug)
    saved = await saved_routes.list_routes(user_id, slug)
    history = await completed_routes.list_snapshots(user_id, slug)
    completed_ids = set(await completed_routes.list_route_ids(user_id, slug))

    known = {place.slug for place in catalog.places}
    valid_favorites = [place for place in favorite_slugs if place in known]
    valid_visited = [place for place in visited_slugs if place in known]

    # Snapshots survive deletion from saved routes, just as in Telegram chat.
    saved_view = [
        _route_view(route, catalog, completed=route.route_id in completed_ids)
        for route in saved
    ]
    history_view = [
        {
            **_route_view(
                SavedRoute(
                    route_id=route.route_id,
                    city_slug=route.city_slug,
                    interest=route.interest,
                    budget_minutes=route.budget_minutes,
                    place_slugs=route.place_slugs,
                    created_at=route.completed_at,
                ),
                catalog,
                completed=True,
            ),
            "completed_at": route.completed_at,
        }
        for route in history
    ]

    return {
        "city_slug": slug,
        "stats": {
            "favorites": len(valid_favorites),
            "visited": len(valid_visited),
            "saved_routes": len(saved_view),
            "completed_routes": await completed_routes.count(user_id, slug),
            "catalog_places": len(catalog.places),
        },
        "favorite_slugs": valid_favorites,
        "visited_slugs": valid_visited,
        "saved_routes": saved_view,
        "completed_routes": history_view,
    }

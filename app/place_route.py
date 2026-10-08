from __future__ import annotations

from app.catalog import CityCatalog
from app.domain import GeneratedRoute, Place
from app.planner import build_ranked_route
from app.route_safety import is_route_stop_available
from app.saved_routes import PLACE_ROUTE_INTEREST
from app.similarity import find_similar_places


def build_place_route(
    catalog: CityCatalog,
    origin_slug: str,
    *,
    budget_minutes: int,
) -> GeneratedRoute | None:
    origin = catalog.place_by_slug(origin_slug)
    if origin is None or not is_route_stop_available(origin):
        return None

    similar = find_similar_places(
        catalog,
        origin.slug,
        limit=10,
    )
    nearby = catalog.nearby_places(
        origin.slug,
        radius_km=5.0,
        limit=12,
    )

    candidates = _deduplicate_places(
        (
            origin,
            *(item.place for item in similar),
            *(place for place, _ in nearby),
        )
    )

    return build_ranked_route(
        candidates,
        budget_minutes=budget_minutes,
        route_interest=PLACE_ROUTE_INTEREST,
    )


def _deduplicate_places(
    places: tuple[Place, ...],
) -> tuple[Place, ...]:
    seen: set[str] = set()
    result: list[Place] = []

    for place in places:
        if place.slug in seen:
            continue
        seen.add(place.slug)
        result.append(place)

    return tuple(result)

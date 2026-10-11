"""Strict Mini App route previews and server-rebuilt saves.

No client-supplied place list is ever written to SQLite.
"""

from __future__ import annotations

from itertools import pairwise
from math import ceil
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.catalog import CityCatalog, distance_km
from app.domain import GeneratedRoute
from app.maps import google_maps_route_links
from app.planner import (
    INTEREST_LABELS,
    MAX_GENERATED_WALK_LEG_KM,
    WALKING_SPEED_KMH,
    build_route,
)
from app.route_safety import is_route_stop_available
from app.route_timing import route_timing
from app.saved_routes import route_id_for


class RouteBuildRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    budget_minutes: Literal[120, 240, 360]
    interest: Literal[
        "classic", "museums", "architecture", "walks",
        "unusual", "family", "free",
    ]
    exclude_visited: bool = False


class SaveBuiltRouteRequest(RouteBuildRequest):
    expected_route_id: str = Field(
        min_length=16, max_length=16, pattern=r"^[0-9a-f]{16}$"
    )


class RouteEditRequest(RouteBuildRequest):
    """Edit only stops from an independently reconstructed canonical route."""

    base_route_id: str = Field(
        min_length=16, max_length=16, pattern=r"^[0-9a-f]{16}$"
    )
    place_slugs: list[str] = Field(min_length=1, max_length=32)


class SaveEditedRouteRequest(RouteEditRequest):
    expected_route_id: str = Field(
        min_length=16, max_length=16, pattern=r"^[0-9a-f]{16}$"
    )


def build_miniapp_route(
    catalog: CityCatalog,
    body: RouteBuildRequest,
    *,
    excluded_slugs: tuple[str, ...] = (),
) -> GeneratedRoute | None:
    return build_route(
        catalog,
        budget_minutes=body.budget_minutes,
        interest=body.interest,
        excluded_slugs=excluded_slugs if body.exclude_visited else (),
    )


def edited_miniapp_route(
    catalog: CityCatalog,
    body: RouteEditRequest,
    *,
    excluded_slugs: tuple[str, ...] = (),
) -> GeneratedRoute:
    """Reject forged additions, stale source routes and unsafe reordered legs.

    The user's editable pool comes exclusively from the server's canonical
    planner output for the same city, budget, interest and visited filter.
    """
    baseline = build_miniapp_route(catalog, body, excluded_slugs=excluded_slugs)
    if baseline is None:
        raise ValueError("The original route is no longer available")
    baseline_slugs = tuple(place.slug for place in baseline.places)
    expected_base = route_id_for(
        catalog.slug, baseline.interest, baseline.budget_minutes, baseline_slugs
    )
    if expected_base != body.base_route_id:
        raise ValueError("The original route changed; rebuild it before editing")

    wanted = body.place_slugs
    if len(wanted) != len(set(wanted)):
        raise ValueError("Duplicate route stops are not allowed")
    if not set(wanted).issubset(baseline_slugs):
        raise ValueError("Stops must come from the original generated route")

    known = {place.slug: place for place in baseline.places}
    places = tuple(known[slug] for slug in wanted)
    if not all(
        is_route_stop_available(place) and place.visit_minutes > 0
        for place in places
    ):
        raise ValueError("Unavailable route stop")

    total_minutes = sum(place.visit_minutes for place in places)
    distance = 0.0
    for left, right in pairwise(places):
        leg_km = distance_km(left, right)
        if leg_km > MAX_GENERATED_WALK_LEG_KM:
            raise ValueError("Walking leg exceeds the safe 5 km straight-line bound")
        total_minutes += ceil(leg_km / WALKING_SPEED_KMH * 60)
        distance += leg_km
    if total_minutes > body.budget_minutes:
        raise ValueError("Edited route exceeds the selected time budget")
    return GeneratedRoute(
        interest=body.interest,
        budget_minutes=body.budget_minutes,
        estimated_minutes=total_minutes,
        distance_km=round(distance, 1),
        places=places,
    )


def route_preview(catalog: CityCatalog, route: GeneratedRoute) -> dict:
    timing = route_timing(route)
    places = route.places
    return {
        "city_slug": catalog.slug,
        "route_id": route_id_for(
            catalog.slug, route.interest, route.budget_minutes,
            tuple(place.slug for place in places),
        ),
        "interest": route.interest,
        "interest_label": INTEREST_LABELS[route.interest],
        "budget_minutes": route.budget_minutes,
        "estimated_minutes": route.estimated_minutes,
        "visit_minutes": timing.visit_minutes,
        "walking_minutes": timing.walking_minutes,
        "spare_minutes": timing.spare_minutes,
        "distance_km": route.distance_km,
        "places": [
            {
                "slug": place.slug,
                "title": place.title,
                "emoji": place.emoji,
                "visit_minutes": place.visit_minutes,
                "district": place.district,
                "latitude": place.latitude,
                "longitude": place.longitude,
            }
            for place in places
        ],
        "map_links": [
            {"url": link.url, "mode": link.mode}
            for link in google_maps_route_links(places)
        ],
    }

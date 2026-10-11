"""Strict Mini App route previews and server-rebuilt saves.

No client-supplied place list is ever written to SQLite.
"""

from __future__ import annotations

from itertools import pairwise
from math import ceil
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.catalog import CityCatalog, distance_km
from app.domain import GeneratedRoute, Place
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


class RouteAlternativesRequest(RouteEditRequest):
    stop_index: int = Field(ge=0, lt=32)


class RouteReplacementRequest(RouteAlternativesRequest):
    candidate_slug: str = Field(min_length=1, max_length=120)


class SaveReplacedRouteRequest(RouteReplacementRequest):
    expected_route_id: str = Field(
        min_length=16, max_length=16, pattern=r"^[0-9a-f]{16}$"
    )


MAX_ALTERNATIVES = 8


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

    return _validated_route(
        body.interest, body.budget_minutes, places
    )


def _validated_route(
    interest: str, budget_minutes: int, places: tuple[Place, ...],
) -> GeneratedRoute:
    if not places:
        raise ValueError("At least one stop must remain")
    if len({place.slug for place in places}) != len(places):
        raise ValueError("Duplicate route stops are not allowed")
    if any(
        not is_route_stop_available(place) or place.visit_minutes <= 0
        for place in places
    ):
        raise ValueError("Unavailable route stop")
    minutes = sum(place.visit_minutes for place in places)
    distance = 0.0
    for left, right in pairwise(places):
        leg = distance_km(left, right)
        if leg > MAX_GENERATED_WALK_LEG_KM:
            raise ValueError("Walking leg exceeds the safe 5 km straight-line bound")
        minutes += ceil(leg / WALKING_SPEED_KMH * 60)
        distance += leg
    if minutes > budget_minutes:
        raise ValueError("Edited route exceeds the selected time budget")
    return GeneratedRoute(
        interest=interest,
        budget_minutes=budget_minutes,
        estimated_minutes=minutes,
        distance_km=round(distance, 1),
        places=places,
    )


def alternative_routes(
    catalog: CityCatalog,
    body: RouteAlternativesRequest,
    *,
    excluded_slugs: tuple[str, ...] = (),
) -> tuple[tuple[Place, GeneratedRoute], ...]:
    """Shortlist server-verified substitutions outside the canonical route."""
    original = edited_miniapp_route(
        catalog, body, excluded_slugs=excluded_slugs
    )
    if body.stop_index >= len(original.places):
        raise ValueError("Invalid stop index")
    baseline = build_miniapp_route(
        catalog, body, excluded_slugs=excluded_slugs
    )
    if baseline is None:
        raise ValueError("The original route is no longer available")
    baseline_slugs = {place.slug for place in baseline.places}
    excluded = set(excluded_slugs) if body.exclude_visited else set()
    previous = original.places[body.stop_index]
    proposals = []
    for candidate in catalog.places:
        if candidate.slug in baseline_slugs or candidate.slug in excluded:
            continue
        if not is_route_stop_available(candidate) or candidate.visit_minutes <= 0:
            continue
        revised_places = list(original.places)
        revised_places[body.stop_index] = candidate
        try:
            revised = _validated_route(
                body.interest, body.budget_minutes, tuple(revised_places)
            )
        except ValueError:
            continue
        rank = (
            int(candidate.category != previous.category),
            distance_km(candidate, previous),
            abs(candidate.visit_minutes - previous.visit_minutes),
            candidate.slug,
        )
        proposals.append((rank, candidate, revised))
    proposals.sort(key=lambda item: item[0])
    return tuple(
        (candidate, route)
        for _, candidate, route in proposals[:MAX_ALTERNATIVES]
    )


def replaced_miniapp_route(
    catalog: CityCatalog,
    body: RouteReplacementRequest,
    *,
    excluded_slugs: tuple[str, ...] = (),
) -> GeneratedRoute:
    for candidate, route in alternative_routes(
        catalog, body, excluded_slugs=excluded_slugs
    ):
        if candidate.slug == body.candidate_slug:
            return route
    raise ValueError("Candidate is not among safe suggested alternatives")


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

"""Strict Mini App route previews and server-rebuilt saves.

No client-supplied place list is ever written to SQLite.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.catalog import CityCatalog
from app.domain import GeneratedRoute
from app.maps import google_maps_route_links
from app.planner import INTEREST_LABELS, build_route
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

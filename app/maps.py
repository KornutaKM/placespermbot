"""Google Maps deep links with explicit long-distance transport boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise
from typing import Literal
from urllib.parse import urlencode

from app.catalog import distance_km
from app.domain import Place
from app.route_safety import LONG_WALKING_LEG_KM

GOOGLE_MAPS_SEARCH_URL = "https://www.google.com/maps/search/"
GOOGLE_MAPS_DIRECTIONS_URL = "https://www.google.com/maps/dir/"
MAX_POINTS_PER_DIRECTIONS_LINK = 5


@dataclass(frozen=True, slots=True)
class RouteMapLink:
    url: str
    mode: Literal["walking", "transit", "place"]
    first_slug: str
    last_slug: str


def google_maps_route_links(places: tuple[Place, ...]) -> tuple[RouteMapLink, ...]:
    """Split at long legs, which must never be presented as walking links."""
    if not places:
        return ()
    if len(places) == 1:
        return (
            RouteMapLink(
                google_maps_place_url(places[0]),
                "place",
                places[0].slug,
                places[0].slug,
            ),
        )

    result: list[RouteMapLink] = []
    walking_group = [places[0]]
    for first, second in pairwise(places):
        if distance_km(first, second) > LONG_WALKING_LEG_KM:
            result.extend(_walking_links(tuple(walking_group)))
            result.append(
                RouteMapLink(
                    _google_maps_directions_url((first, second), travelmode="transit"),
                    "transit",
                    first.slug,
                    second.slug,
                )
            )
            walking_group = [second]
        else:
            walking_group.append(second)
    result.extend(_walking_links(tuple(walking_group)))
    return tuple(result)


def google_maps_route_urls(places: tuple[Place, ...]) -> tuple[str, ...]:
    """Compatibility API: URLs retain the same stop order as route links."""
    return tuple(link.url for link in google_maps_route_links(places))


def _walking_links(places: tuple[Place, ...]) -> tuple[RouteMapLink, ...]:
    if len(places) < 2:
        return ()
    result: list[RouteMapLink] = []
    start = 0
    while start < len(places) - 1:
        segment = places[start : start + MAX_POINTS_PER_DIRECTIONS_LINK]
        result.append(
            RouteMapLink(
                _google_maps_directions_url(segment, travelmode="walking"),
                "walking",
                segment[0].slug,
                segment[-1].slug,
            )
        )
        if start + len(segment) >= len(places):
            break
        start += len(segment) - 1
    return tuple(result)


def google_maps_directions_to_place_url(place: Place) -> str:
    query = urlencode(
        {
            "api": "1",
            "destination": _coordinates(place),
            "travelmode": "walking",
            "dir_action": "navigate",
        }
    )
    return f"{GOOGLE_MAPS_DIRECTIONS_URL}?{query}"


def google_maps_place_url(place: Place) -> str:
    query = urlencode({"api": "1", "query": _coordinates(place)})
    return f"{GOOGLE_MAPS_SEARCH_URL}?{query}"


def _google_maps_directions_url(
    places: tuple[Place, ...], *, travelmode: Literal["walking", "transit"]
) -> str:
    if len(places) < 2:
        raise ValueError("directions URL requires at least two places")
    if len(places) > MAX_POINTS_PER_DIRECTIONS_LINK:
        raise ValueError("directions URL exceeds mobile-compatible point limit")
    parameters: dict[str, str] = {
        "api": "1",
        "origin": _coordinates(places[0]),
        "destination": _coordinates(places[-1]),
        "travelmode": travelmode,
    }
    waypoints = places[1:-1]
    if waypoints:
        parameters["waypoints"] = "|".join(_coordinates(place) for place in waypoints)
    return f"{GOOGLE_MAPS_DIRECTIONS_URL}?{urlencode(parameters)}"


def _coordinates(place: Place) -> str:
    return f"{place.latitude:.6f},{place.longitude:.6f}"

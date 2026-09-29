from __future__ import annotations

from urllib.parse import urlencode

from app.domain import Place

GOOGLE_MAPS_SEARCH_URL = "https://www.google.com/maps/search/"
GOOGLE_MAPS_DIRECTIONS_URL = "https://www.google.com/maps/dir/"
MAX_POINTS_PER_DIRECTIONS_LINK = 5


def google_maps_route_urls(places: tuple[Place, ...]) -> tuple[str, ...]:
    if not places:
        return ()
    if len(places) == 1:
        return (google_maps_place_url(places[0]),)

    urls: list[str] = []
    start = 0

    while start < len(places) - 1:
        segment = places[start : start + MAX_POINTS_PER_DIRECTIONS_LINK]
        urls.append(_google_maps_directions_url(segment))

        if start + len(segment) >= len(places):
            break

        start += len(segment) - 1

    return tuple(urls)


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
    query = urlencode(
        {
            "api": "1",
            "query": _coordinates(place),
        }
    )
    return f"{GOOGLE_MAPS_SEARCH_URL}?{query}"


def _google_maps_directions_url(places: tuple[Place, ...]) -> str:
    if len(places) < 2:
        raise ValueError("directions URL requires at least two places")
    if len(places) > MAX_POINTS_PER_DIRECTIONS_LINK:
        raise ValueError("directions URL exceeds mobile-compatible point limit")

    parameters: dict[str, str] = {
        "api": "1",
        "origin": _coordinates(places[0]),
        "destination": _coordinates(places[-1]),
        "travelmode": "walking",
    }

    waypoints = places[1:-1]
    if waypoints:
        parameters["waypoints"] = "|".join(_coordinates(place) for place in waypoints)

    return f"{GOOGLE_MAPS_DIRECTIONS_URL}?{urlencode(parameters)}"


def _coordinates(place: Place) -> str:
    return f"{place.latitude:.6f},{place.longitude:.6f}"

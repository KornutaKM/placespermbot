"""Stateless, mobile-safe stop removal for freshly generated walking routes.

Callback encodings reuse the immutable savegen snapshot. They are never
authorization tokens or instructions to modify SQLite.
"""

from __future__ import annotations

from itertools import pairwise
from math import ceil

from app.catalog import CityCatalog, distance_km
from app.domain import GeneratedRoute
from app.planner import (
    INTEREST_LABELS,
    MAX_GENERATED_WALK_LEG_KM,
    WALKING_SPEED_KMH,
)
from app.route_safety import is_route_stop_available
from app.saved_routes import RouteSnapshot, parse_save_callback

EDIT_PREFIX = "editgen:"
BACK_PREFIX = "backgen:"
REMOVE_PREFIX = "dropg:"
SAVE_PREFIX = "savegen:"


def edit_callback(save_callback: str) -> str:
    return _replace_prefix(save_callback, EDIT_PREFIX)


def back_callback(save_callback: str) -> str:
    return _replace_prefix(save_callback, BACK_PREFIX)


def remove_callback(save_callback: str, index: int) -> str:
    if not 0 <= index <= 255:
        raise ValueError("Stop index cannot be encoded")
    encoded = _save_payload(save_callback)
    result = f"{REMOVE_PREFIX}{index:02x}{encoded}"
    _check_callback_size(result)
    return result


def parse_editor_callback(data: str, catalog: CityCatalog) -> RouteSnapshot:
    if not data.startswith((EDIT_PREFIX, BACK_PREFIX)):
        raise ValueError("Unsupported editor callback")
    prefix = EDIT_PREFIX if data.startswith(EDIT_PREFIX) else BACK_PREFIX
    return _parse_snapshot(data.removeprefix(prefix), catalog)


def parse_remove_callback(
    data: str, catalog: CityCatalog
) -> tuple[RouteSnapshot, int]:
    if not data.startswith(REMOVE_PREFIX):
        raise ValueError("Unsupported remove callback")
    payload = data.removeprefix(REMOVE_PREFIX)
    if len(payload) < 3:
        raise ValueError("Invalid remove callback")
    try:
        index = int(payload[:2], 16)
    except ValueError as exc:
        raise ValueError("Invalid remove index") from exc
    snapshot = _parse_snapshot(payload[2:], catalog)
    if index >= len(snapshot.places):
        raise ValueError("Stop index out of bounds")
    return snapshot, index


def route_after_removal(
    snapshot: RouteSnapshot, index: int
) -> GeneratedRoute:
    if snapshot.interest not in INTEREST_LABELS:
        raise ValueError("Only regular generated routes can be edited")
    if not 0 <= index < len(snapshot.places):
        raise ValueError("Stop index out of bounds")
    places = snapshot.places[:index] + snapshot.places[index + 1 :]
    if not places:
        raise ValueError("At least one route stop must remain")
    if len({place.slug for place in places}) != len(places):
        raise ValueError("Duplicate route stops")
    if any(
        not is_route_stop_available(place) or place.visit_minutes <= 0
        for place in places
    ):
        raise ValueError("One or more route stops are unavailable")

    estimated_minutes = sum(place.visit_minutes for place in places)
    total_distance = 0.0
    for previous, current in pairwise(places):
        leg = distance_km(previous, current)
        if leg > MAX_GENERATED_WALK_LEG_KM:
            raise ValueError("Removing this stop creates a long walking leg")
        total_distance += leg
        estimated_minutes += ceil(leg / WALKING_SPEED_KMH * 60)

    if estimated_minutes > snapshot.budget_minutes:
        raise ValueError("The edited route exceeds its time budget")
    return GeneratedRoute(
        interest=snapshot.interest,
        budget_minutes=snapshot.budget_minutes,
        estimated_minutes=estimated_minutes,
        distance_km=round(total_distance, 1),
        places=places,
    )


def _parse_snapshot(payload: str, catalog: CityCatalog) -> RouteSnapshot:
    snapshot = parse_save_callback(SAVE_PREFIX + payload, catalog)
    if snapshot.interest not in INTEREST_LABELS:
        raise ValueError("Only ordinary generated routes are editable")
    if len(snapshot.places) < 2:
        raise ValueError("Route must have at least two stops for editing")
    if len(snapshot.places) > 256:
        raise ValueError("Too many stops for editor callbacks")
    return snapshot


def _replace_prefix(save_callback: str, prefix: str) -> str:
    result = prefix + _save_payload(save_callback)
    _check_callback_size(result)
    return result


def _save_payload(save_callback: str) -> str:
    if not save_callback.startswith(SAVE_PREFIX):
        raise ValueError("Invalid route snapshot callback")
    return save_callback.removeprefix(SAVE_PREFIX)


def _check_callback_size(value: str) -> None:
    if len(value.encode("utf-8")) > 64:
        raise ValueError("Telegram callback data limit exceeded")

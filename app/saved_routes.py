from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from app.catalog import CityCatalog
from app.domain import GeneratedRoute, Place

_INTEREST_CODES = {
    "classic": "c",
    "museums": "m",
    "architecture": "a",
    "walks": "w",
    "unusual": "u",
    "family": "f",
    "free": "r",
}
_CODE_INTERESTS = {value: key for key, value in _INTEREST_CODES.items()}
_BASE36 = "0123456789abcdefghijklmnopqrstuvwxyz"
_INDEX_WIDTH = 2
_CHECKSUM_LENGTH = 8
CALLBACK_PREFIX = "savegen:"


@dataclass(frozen=True, slots=True)
class SavedRoute:
    route_id: str
    city_slug: str
    interest: str
    budget_minutes: int
    place_slugs: tuple[str, ...]
    created_at: str


@dataclass(frozen=True, slots=True)
class RouteSnapshot:
    interest: str
    budget_minutes: int
    places: tuple[Place, ...]


def build_save_callback(catalog: CityCatalog, route: GeneratedRoute) -> str:
    code = _INTEREST_CODES.get(route.interest)
    if code is None:
        raise ValueError("Unsupported route interest")

    if route.budget_minutes not in {120, 240, 360}:
        raise ValueError("Unsupported route budget")

    indices = []
    for place in route.places:
        try:
            index = catalog.places.index(place)
        except ValueError as exc:
            raise ValueError("Route contains a place outside the catalog") from exc
        indices.append(_encode_index(index))

    packed_indices = "".join(indices)
    payload = f"{code}:{route.budget_minutes // 60}:{packed_indices}"
    checksum = _checksum(
        catalog.slug,
        route.interest,
        route.budget_minutes,
        tuple(place.slug for place in route.places),
    )
    callback = f"{CALLBACK_PREFIX}{payload}:{checksum}"
    if len(callback.encode("utf-8")) > 64:
        raise ValueError("Route snapshot exceeds Telegram callback_data limit")
    return callback


def parse_save_callback(
    callback_data: str,
    catalog: CityCatalog,
) -> RouteSnapshot:
    if not callback_data.startswith(CALLBACK_PREFIX):
        raise ValueError("Invalid saved-route callback prefix")

    payload = callback_data.removeprefix(CALLBACK_PREFIX)
    try:
        code, raw_hours, packed_indices, checksum = payload.split(":", 3)
        interest = _CODE_INTERESTS[code]
        budget_minutes = int(raw_hours) * 60
    except (ValueError, KeyError) as exc:
        raise ValueError("Invalid saved-route callback") from exc

    if budget_minutes not in {120, 240, 360}:
        raise ValueError("Unsupported saved-route budget")
    if not packed_indices or len(packed_indices) % _INDEX_WIDTH:
        raise ValueError("Invalid saved-route place payload")

    places: list[Place] = []
    for offset in range(0, len(packed_indices), _INDEX_WIDTH):
        index = _decode_index(packed_indices[offset : offset + _INDEX_WIDTH])
        if index >= len(catalog.places):
            raise ValueError("Saved-route catalog index is stale")
        places.append(catalog.places[index])

    slugs = tuple(place.slug for place in places)
    expected = _checksum(catalog.slug, interest, budget_minutes, slugs)
    if checksum != expected:
        raise ValueError("Saved-route snapshot checksum mismatch")

    return RouteSnapshot(
        interest=interest,
        budget_minutes=budget_minutes,
        places=tuple(places),
    )


def route_id_for(
    city_slug: str,
    interest: str,
    budget_minutes: int,
    place_slugs: tuple[str, ...],
) -> str:
    payload = "|".join(
        (city_slug, interest, str(budget_minutes), *place_slugs)
    )
    return sha256(payload.encode("utf-8")).hexdigest()[:16]


def _checksum(
    city_slug: str,
    interest: str,
    budget_minutes: int,
    place_slugs: tuple[str, ...],
) -> str:
    payload = "|".join(
        (city_slug, interest, str(budget_minutes), *place_slugs)
    )
    return sha256(payload.encode("utf-8")).hexdigest()[:_CHECKSUM_LENGTH]


def _encode_index(index: int) -> str:
    if index < 0 or index >= 36**_INDEX_WIDTH:
        raise ValueError("Catalog index exceeds route snapshot capacity")
    high, low = divmod(index, 36)
    return _BASE36[high] + _BASE36[low]


def _decode_index(value: str) -> int:
    if len(value) != _INDEX_WIDTH:
        raise ValueError("Invalid catalog index width")
    try:
        return _BASE36.index(value[0]) * 36 + _BASE36.index(value[1])
    except ValueError as exc:
        raise ValueError("Invalid catalog index encoding") from exc

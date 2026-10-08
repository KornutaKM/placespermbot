"""Shared eligibility and geodesic route checks (never a walking ETA)."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise

from app.catalog import distance_km
from app.domain import Place

INACCESSIBLE_TAGS = frozenset({"закрыто", "недоступно"})
LONG_WALKING_LEG_KM = 8.0


def is_route_stop_available(place: Place) -> bool:
    """Block only explicit editorial tags, not incidental wording."""
    return not INACCESSIBLE_TAGS.intersection(place.tags)


@dataclass(frozen=True, slots=True)
class RouteGeography:
    straight_line_km: float
    longest_leg_km: float
    long_legs: tuple[tuple[str, str, float], ...]


def route_geography(places: tuple[Place, ...]) -> RouteGeography:
    total = 0.0
    longest = 0.0
    flagged: list[tuple[str, str, float]] = []
    for first, second in pairwise(places):
        leg = distance_km(first, second)
        total += leg
        longest = max(longest, leg)
        if leg > LONG_WALKING_LEG_KM:
            flagged.append((first.slug, second.slug, round(leg, 1)))
    return RouteGeography(round(total, 2), round(longest, 2), tuple(flagged))


def route_access_warnings(places: tuple[Place, ...]) -> tuple[str, ...]:
    warnings: list[str] = []
    unavailable = [place for place in places if not is_route_stop_available(place)]
    if unavailable:
        warnings.append(
            "Некоторые точки отмечены закрытыми и не подходят для посещения: "
            + ", ".join(place.title for place in unavailable)
        )
    if route_geography(places).long_legs:
        warnings.append(
            "Между отдельными точками более 8 км по прямой. "
            "Может потребоваться транспорт: проверьте пересадки и доступность дороги."
        )
    return tuple(warnings)

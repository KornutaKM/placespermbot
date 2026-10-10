"""Consistent, arithmetic-only time breakdown for generated walking routes."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain import GeneratedRoute


@dataclass(frozen=True, slots=True)
class RouteTiming:
    visit_minutes: int
    walking_minutes: int
    spare_minutes: int


def route_timing(route: GeneratedRoute) -> RouteTiming:
    visits = sum(place.visit_minutes for place in route.places)
    if visits < 0 or visits > route.estimated_minutes:
        raise ValueError("Invalid generated route visit time")
    if route.estimated_minutes > route.budget_minutes:
        raise ValueError("Generated route exceeds time budget")

    return RouteTiming(
        visit_minutes=visits,
        walking_minutes=route.estimated_minutes - visits,
        spare_minutes=route.budget_minutes - route.estimated_minutes,
    )


def route_timing_text(route: GeneratedRoute) -> str:
    timing = route_timing(route)
    return (
        f"Из них: осмотр ~{timing.visit_minutes} мин, "
        f"пешие переходы ~{timing.walking_minutes} мин\n"
        f"Резерв бюджета: ~{timing.spare_minutes} мин\n"
    )

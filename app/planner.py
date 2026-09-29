from __future__ import annotations

from math import ceil

from app.catalog import CityCatalog, distance_km
from app.domain import GeneratedRoute, Place

WALKING_SPEED_KMH = 4.5

INTEREST_LABELS: dict[str, str] = {
    "classic": "🏛 Классический Петербург",
    "museums": "🖼 Музеи",
    "architecture": "🏛 Архитектура",
    "walks": "🌿 Прогулки",
    "unusual": "✨ Необычные места",
    "family": "👨‍👩‍👧 С детьми",
    "free": "💸 Бесплатно",
}


def build_route(
    catalog: CityCatalog,
    *,
    budget_minutes: int,
    interest: str,
) -> GeneratedRoute | None:
    if budget_minutes <= 0:
        raise ValueError("budget_minutes must be positive")
    if interest not in INTEREST_LABELS:
        raise ValueError(f"Unsupported interest: {interest}")

    candidates = _candidates(catalog, interest)
    if not candidates:
        return None

    first = next(
        (place for place in candidates if place.visit_minutes <= budget_minutes),
        None,
    )
    if first is None:
        return None

    selected = [first]
    remaining = [place for place in candidates if place.slug != first.slug]
    used_minutes = first.visit_minutes
    total_distance = 0.0

    while remaining:
        current = selected[-1]
        ranked = sorted(
            remaining,
            key=lambda place: (
                distance_km(current, place),
                candidates.index(place),
                place.title,
            ),
        )

        chosen: Place | None = None
        chosen_distance = 0.0
        chosen_cost = 0

        for place in ranked:
            leg_distance = distance_km(current, place)
            walking_minutes = _walking_minutes(leg_distance)
            incremental_cost = walking_minutes + place.visit_minutes

            if used_minutes + incremental_cost <= budget_minutes:
                chosen = place
                chosen_distance = leg_distance
                chosen_cost = incremental_cost
                break

        if chosen is None:
            break

        selected.append(chosen)
        remaining.remove(chosen)
        used_minutes += chosen_cost
        total_distance += chosen_distance

    return GeneratedRoute(
        interest=interest,
        budget_minutes=budget_minutes,
        estimated_minutes=used_minutes,
        distance_km=round(total_distance, 1),
        places=tuple(selected),
    )


def _walking_minutes(distance: float) -> int:
    if distance <= 0:
        return 0
    return ceil((distance / WALKING_SPEED_KMH) * 60)


def _candidates(catalog: CityCatalog, interest: str) -> list[Place]:
    if interest == "classic":
        return [
            place
            for place in catalog.places
            if place.category in {"sights", "parks"}
            or (place.category == "unusual" and "центр" in place.tags)
        ]
    if interest == "museums":
        return [place for place in catalog.places if place.category == "museums"]
    if interest == "architecture":
        return [
            place
            for place in catalog.places
            if "архитектура" in place.tags or "собор" in place.tags
        ]
    if interest == "walks":
        return [
            place
            for place in catalog.places
            if place.category == "parks" or "прогулка" in place.tags
        ]
    if interest == "unusual":
        return [place for place in catalog.places if place.category == "unusual"]
    if interest == "family":
        return [place for place in catalog.places if "с детьми" in place.tags]
    if interest == "free":
        return [place for place in catalog.places if place.is_free]
    return []

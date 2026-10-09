from __future__ import annotations

from math import ceil

from app.catalog import CityCatalog, coordinates_distance_km, distance_km
from app.domain import GeneratedRoute, Place
from app.route_safety import is_route_stop_available

WALKING_SPEED_KMH = 4.5
MAX_GENERATED_WALK_LEG_KM = 5.0

INTEREST_LABELS: dict[str, str] = {
    "classic": "🏛 Главные места",
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
    start_latitude: float | None = None,
    start_longitude: float | None = None,
    prefer_variety: bool = False,
) -> GeneratedRoute | None:
    if interest not in INTEREST_LABELS:
        raise ValueError(f"Unsupported interest: {interest}")

    return build_ranked_route(
        tuple(_candidates(catalog, interest)),
        budget_minutes=budget_minutes,
        route_interest=interest,
        start_latitude=start_latitude,
        start_longitude=start_longitude,
    )


def build_ranked_route(
    candidates: tuple[Place, ...],
    *,
    budget_minutes: int,
    route_interest: str,
    start_latitude: float | None = None,
    start_longitude: float | None = None,
    prefer_variety: bool = False,
) -> GeneratedRoute | None:
    if budget_minutes <= 0:
        raise ValueError("budget_minutes must be positive")
    if not route_interest.strip():
        raise ValueError("route_interest must not be blank")

    _validate_origin(start_latitude, start_longitude)

    ordered = _deduplicate_candidates(candidates)
    if not ordered:
        return None

    first, first_distance, first_cost = _choose_first(
        ordered,
        budget_minutes=budget_minutes,
        start_latitude=start_latitude,
        start_longitude=start_longitude,
    )
    if first is None:
        return None

    selected = [first]
    remaining = [place for place in ordered if place.slug != first.slug]
    used_minutes = first_cost
    total_distance = first_distance

    while remaining:
        current = selected[-1]
        ranked = sorted(
            remaining,
            key=lambda place: _next_stop_rank(
                place,
                current=current,
                selected=selected,
                ordered=ordered,
                prefer_variety=prefer_variety,
            ),
        )

        chosen: Place | None = None
        chosen_distance = 0.0
        chosen_cost = 0

        for place in ranked:
            leg_distance = distance_km(current, place)
            if leg_distance > MAX_GENERATED_WALK_LEG_KM:
                continue
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
        interest=route_interest,
        budget_minutes=budget_minutes,
        estimated_minutes=used_minutes,
        distance_km=round(total_distance, 1),
        places=tuple(selected),
    )



def _next_stop_rank(
    place: Place,
    *,
    current: Place,
    selected: list[Place],
    ordered: list[Place],
    prefer_variety: bool,
) -> tuple[int, int, float, int, str]:
    if not prefer_variety:
        return (0, 0, distance_km(current, place), ordered.index(place), place.title)

    used_categories = {item.category for item in selected}
    used_districts = {item.district for item in selected}
    return (
        int(place.category in used_categories),
        int(place.district in used_districts),
        distance_km(current, place),
        ordered.index(place),
        place.title,
    )

def _deduplicate_candidates(candidates: tuple[Place, ...]) -> list[Place]:
    seen: set[str] = set()
    ordered: list[Place] = []
    for place in candidates:
        if not is_route_stop_available(place) or place.slug in seen:
            continue
        seen.add(place.slug)
        ordered.append(place)
    return ordered


def _choose_first(
    candidates: list[Place],
    *,
    budget_minutes: int,
    start_latitude: float | None,
    start_longitude: float | None,
) -> tuple[Place | None, float, int]:
    if start_latitude is None or start_longitude is None:
        first = next(
            (place for place in candidates if place.visit_minutes <= budget_minutes),
            None,
        )
        if first is None:
            return None, 0.0, 0
        return first, 0.0, first.visit_minutes

    ranked = sorted(
        candidates,
        key=lambda place: (
            coordinates_distance_km(
                start_latitude,
                start_longitude,
                place.latitude,
                place.longitude,
            ),
            candidates.index(place),
            place.title,
        ),
    )

    for place in ranked:
        start_distance = coordinates_distance_km(
            start_latitude,
            start_longitude,
            place.latitude,
            place.longitude,
        )
        if start_distance > MAX_GENERATED_WALK_LEG_KM:
            continue
        first_cost = _walking_minutes(start_distance) + place.visit_minutes
        if first_cost <= budget_minutes:
            return place, start_distance, first_cost

    return None, 0.0, 0


def _validate_origin(
    start_latitude: float | None,
    start_longitude: float | None,
) -> None:
    if (start_latitude is None) != (start_longitude is None):
        raise ValueError("start coordinates must be provided together")
    if start_latitude is None or start_longitude is None:
        return
    if not -90 <= start_latitude <= 90:
        raise ValueError("start_latitude is out of range")
    if not -180 <= start_longitude <= 180:
        raise ValueError("start_longitude is out of range")


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

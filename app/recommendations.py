from collections.abc import Collection

from app.catalog import CityCatalog
from app.domain import Place
from app.planner import INTEREST_LABELS


def recommend_places(
    catalog: CityCatalog,
    interests: tuple[str, ...],
    *,
    limit: int = 8,
    exclude_slugs: Collection[str] = (),
) -> tuple[Place, ...]:
    if limit <= 0 or not interests:
        return ()

    unknown = set(interests) - set(INTEREST_LABELS)
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ValueError(f"Unsupported interests: {names}")

    excluded = set(exclude_slugs)
    ranked: list[tuple[int, int, Place]] = []
    for index, place in enumerate(catalog.places):
        if place.slug in excluded:
            continue

        score = sum(_interest_score(place, interest) for interest in interests)
        if score > 0:
            ranked.append((score, index, place))

    ranked.sort(key=lambda item: (-item[0], item[1], item[2].title))
    return tuple(place for _, _, place in ranked[:limit])


def _interest_score(place: Place, interest: str) -> int:
    if interest == "classic":
        score = 0
        if place.category == "sights":
            score += 4
        if place.category == "parks":
            score += 2
        if "центр" in place.tags:
            score += 1
        return score

    if interest == "museums":
        return 5 if place.category == "museums" else 0

    if interest == "architecture":
        return 5 if "архитектура" in place.tags or "собор" in place.tags else 0

    if interest == "walks":
        score = 0
        if place.category == "parks":
            score += 4
        if "прогулка" in place.tags:
            score += 3
        return score

    if interest == "unusual":
        return 5 if place.category == "unusual" else 0

    if interest == "family":
        return 5 if "с детьми" in place.tags else 0

    if interest == "free":
        return 4 if place.is_free else 0

    return 0

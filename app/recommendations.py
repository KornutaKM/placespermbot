from collections.abc import Collection
from dataclasses import dataclass

from app.catalog import CityCatalog
from app.domain import Place
from app.planner import INTEREST_LABELS

FAVORITE_BONUS = 1
FAVORITE_AFFINITY_BONUS_CAP = 2
MULTI_INTEREST_BONUS = 2
VISITED_AFFINITY_BONUS_CAP = 3
COMPLETED_ROUTE_AFFINITY_BONUS_CAP = 2

_AFFINITY_IGNORED_TAGS = frozenset(
    {
        "бесплатно",
        "с детьми",
        "центр",
        "прогулка",
    }
)


@dataclass(frozen=True, slots=True)
class PersonalRecommendation:
    place: Place
    score: int
    reasons: tuple[str, ...]


def recommend_personalized(
    catalog: CityCatalog,
    interests: tuple[str, ...],
    *,
    limit: int = 8,
    favorite_slugs: Collection[str] = (),
    visited_slugs: Collection[str] = (),
    completed_route_place_slugs: Collection[str] = (),
    exclude_slugs: Collection[str] = (),
) -> tuple[PersonalRecommendation, ...]:
    if limit <= 0 or not interests:
        return ()

    _validate_interests(interests)

    favorites = set(favorite_slugs)
    favorite_places = tuple(
        place
        for place in catalog.places
        if place.slug in favorites
    )
    visited = set(visited_slugs)
    visited_places = tuple(
        place
        for place in catalog.places
        if place.slug in visited
    )
    completed_route_places_set = set(completed_route_place_slugs)
    completed_route_places = tuple(
        place
        for place in catalog.places
        if place.slug in completed_route_places_set
    )
    excluded = set(exclude_slugs)
    ranked: list[tuple[int, int, PersonalRecommendation]] = []

    for index, place in enumerate(catalog.places):
        if place.slug in excluded:
            continue

        matches = tuple(
            (interest, score)
            for interest in interests
            if (score := _interest_score(place, interest)) > 0
        )
        if not matches:
            continue

        score = sum(match_score for _, match_score in matches)
        reasons = [_interest_reason(matches)]

        if len(matches) > 1:
            score += MULTI_INTEREST_BONUS

        if place.slug in favorites:
            score += FAVORITE_BONUS
            reasons.append("уже в избранном")

        affinity_tags = _favorite_affinity_tags(
            place,
            favorite_places=favorite_places,
        )
        if affinity_tags:
            score += min(
                len(affinity_tags),
                FAVORITE_AFFINITY_BONUS_CAP,
            )
            reasons.append(
                "похоже на избранное: " + ", ".join(affinity_tags)
            )

        visited_affinity_tags = _place_affinity_tags(
            place,
            reference_places=visited_places,
        )
        if visited_affinity_tags:
            score += min(
                len(visited_affinity_tags),
                VISITED_AFFINITY_BONUS_CAP,
            )
            reasons.append(
                "похоже на посещённое: " + ", ".join(visited_affinity_tags)
            )

        completed_route_affinity_tags = _place_affinity_tags(
            place,
            reference_places=completed_route_places,
        )
        if completed_route_affinity_tags:
            score += min(
                len(completed_route_affinity_tags),
                COMPLETED_ROUTE_AFFINITY_BONUS_CAP,
            )
            reasons.append(
                "похоже на пройденный маршрут: "
                + ", ".join(completed_route_affinity_tags)
            )

        recommendation = PersonalRecommendation(
            place=place,
            score=score,
            reasons=tuple(reasons),
        )
        ranked.append((score, index, recommendation))

    ranked.sort(
        key=lambda item: (
            -item[0],
            item[1],
            item[2].place.title,
        )
    )
    return tuple(item[2] for item in ranked[:limit])


def recommend_places(
    catalog: CityCatalog,
    interests: tuple[str, ...],
    *,
    limit: int = 8,
    exclude_slugs: Collection[str] = (),
) -> tuple[Place, ...]:
    if limit <= 0 or not interests:
        return ()

    _validate_interests(interests)

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


def _validate_interests(interests: tuple[str, ...]) -> None:
    unknown = set(interests) - set(INTEREST_LABELS)
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ValueError(f"Unsupported interests: {names}")


def _interest_reason(matches: tuple[tuple[str, int], ...]) -> str:
    labels = tuple(INTEREST_LABELS[interest] for interest, _ in matches)
    if len(labels) == 1:
        return f"интерес: {labels[0]}"
    return "несколько интересов: " + " · ".join(labels)


def _favorite_affinity_tags(
    place: Place,
    *,
    favorite_places: tuple[Place, ...],
) -> tuple[str, ...]:
    return _place_affinity_tags(
        place,
        reference_places=favorite_places,
    )


def _place_affinity_tags(
    place: Place,
    *,
    reference_places: tuple[Place, ...],
) -> tuple[str, ...]:
    candidate_tags = set(place.tags) - _AFFINITY_IGNORED_TAGS
    if not candidate_tags:
        return ()

    shared: set[str] = set()
    for reference in reference_places:
        if reference.slug == place.slug:
            continue

        reference_tags = set(reference.tags) - _AFFINITY_IGNORED_TAGS
        shared.update(candidate_tags & reference_tags)

    return tuple(sorted(shared))


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

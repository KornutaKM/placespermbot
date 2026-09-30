from dataclasses import dataclass

from app.catalog import CityCatalog
from app.domain import Place

_CATEGORY_BONUS = 3
_TAG_BONUS = 2
_IGNORED_TAGS = frozenset(
    {
        "бесплатно",
        "с детьми",
        "центр",
        "прогулка",
    }
)


@dataclass(frozen=True, slots=True)
class SimilarPlace:
    place: Place
    score: int
    reasons: tuple[str, ...]


def find_similar_places(
    catalog: CityCatalog,
    origin_slug: str,
    *,
    limit: int = 5,
) -> tuple[SimilarPlace, ...]:
    if limit <= 0:
        return ()

    origin = catalog.place_by_slug(origin_slug)
    if origin is None:
        return ()

    origin_tags = set(origin.tags) - _IGNORED_TAGS
    ranked: list[tuple[int, int, SimilarPlace]] = []

    for index, candidate in enumerate(catalog.places):
        if candidate.slug == origin.slug:
            continue

        score = 0
        reasons: list[str] = []

        if candidate.category == origin.category:
            score += _CATEGORY_BONUS
            reasons.append("та же категория")

        shared_tags = tuple(
            sorted(
                origin_tags
                & (set(candidate.tags) - _IGNORED_TAGS)
            )
        )
        if shared_tags:
            score += len(shared_tags) * _TAG_BONUS
            reasons.append("общие темы: " + ", ".join(shared_tags))

        if score <= 0:
            continue

        ranked.append(
            (
                score,
                index,
                SimilarPlace(
                    place=candidate,
                    score=score,
                    reasons=tuple(reasons),
                ),
            )
        )

    ranked.sort(
        key=lambda item: (
            -item[0],
            item[1],
            item[2].place.title,
        )
    )
    return tuple(item[2] for item in ranked[:limit])

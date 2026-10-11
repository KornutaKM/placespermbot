"""Bounded, deterministic public search across registered city catalogs.

Uses catalog data only. No Telegram identity, user information or live opening hours.
"""

from __future__ import annotations

from typing import Literal

from app.catalog import CityCatalog, list_catalogs
from app.domain import Place

DiscoveryCategory = Literal[
    "all", "sights", "unusual", "museums", "parks", "family", "free"
]


def _normalize(value: str) -> str:
    return " ".join(value.casefold().replace("ё", "е").split())


def _matches_category(place: Place, category: DiscoveryCategory) -> bool:
    if category == "all":
        return True
    if category == "free":
        return place.is_free
    if category == "family":
        return "с детьми" in place.tags
    return place.category == category


def discover_places(
    query: str,
    *,
    category: DiscoveryCategory = "all",
    offset: int = 0,
    limit: int = 12,
    catalogs: tuple[CityCatalog, ...] | None = None,
) -> dict:
    """Rank places matching *every* search term across city and place fields.

    Ordering is stable under identical catalog data and independent of dict order.
    Only small public DTOs are exposed. Paging happens after global ranking.
    """
    terms = _normalize(query).split()
    if not terms:
        raise ValueError("Search query must not be blank")
    if not 0 <= offset <= 1000 or not 1 <= limit <= 30:
        raise ValueError("Invalid search page")
    if category not in ("all", "sights", "unusual", "museums", "parks", "family", "free"):
        raise ValueError("Invalid category")

    ranked: list[tuple[int, str, str, str, CityCatalog, Place]] = []
    for city in catalogs if catalogs is not None else list_catalogs():
        city_name = _normalize(city.name)
        for place in city.places:
            if not _matches_category(place, category):
                continue
            title = _normalize(place.title)
            tags = _normalize(" ".join(place.tags))
            district = _normalize(place.district)
            summary = _normalize(place.summary)
            fields = (title, tags, district, summary, city_name)
            if not all(any(term in field for field in fields) for term in terms):
                continue
            score = sum(
                12 * (term in title)
                + 6 * (term in tags)
                + 4 * (term in city_name)
                + 3 * (term in district)
                + (term in summary)
                for term in terms
            )
            if _normalize(query) == title:
                score += 24
            ranked.append((
                -score, city.name.casefold(), place.title.casefold(),
                place.slug, city, place,
            ))

    ranked.sort(key=lambda row: row[:4])
    total = len(ranked)
    results = []
    for _, _, _, _, city, place in ranked[offset:offset + limit]:
        results.append({
            "city_slug": city.slug,
            "city_name": city.name,
            "place_slug": place.slug,
            "title": place.title,
            "summary": place.summary,
            "category": place.category,
            "category_label": city.category_labels.get(place.category, place.category),
            "district": place.district,
            "emoji": place.emoji,
            "visit_minutes": place.visit_minutes,
            "is_free": place.is_free,
        })
    return {
        "query": query.strip(),
        "category": category,
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": offset + limit < total,
        "places": results,
    }

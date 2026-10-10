"""Reviewed long-distance links in curated routes.

Keys are precise stop-to-stop contracts. New, removed, or moved >8 km
straight-line legs fail CI until an editor updates this registry.
An entry is not a claim that a particular transit service operates.
"""

from __future__ import annotations

from collections.abc import Iterable

from app.catalog import CityCatalog, list_catalogs
from app.route_safety import route_geography

TransferKey = tuple[str, str, str, str]

REVIEWED_TRANSFERS: dict[TransferKey, str] = {
    ("moscow", "moscow-contemporary-art", "winzavod", "moscow-city"):
        "Между Винзаводом и Москва-Сити необходимо отдельно спланировать транспорт.",
    ("moscow", "moscow-modern", "vdnh", "moscow-city"):
        "ВДНХ и Москва-Сити находятся в разных районах; проверьте городской транспорт.",
    ("moscow", "moscow-parks", "gorky-park-moscow", "kolomenskoye"):
        "Между Парком Горького и Коломенским требуется отдельный переезд.",
    ("novosibirsk", "nsk-science", "akademgorodok-nsk", "railway-museum-nsk"):
        "От Академгородка до музея железнодорожной техники нужен транспорт.",
    ("saint-petersburg", "spb-family-day", "grand-maket-russia", "botanical-garden"):
        "От Гранд Макета до Ботанического сада потребуется отдельный переезд.",
    ("samara", "samara-views", "ladya-monument", "helicopter-viewpoint-samara"):
        "От Ладьи до Вертолётной площадки необходим транспорт.",
    ("sochi", "sochi-matsesta-nature", "matsesta-sochi", "zmeykovskie-waterfalls"):
        "От Старой Мацесты до Змейковских водопадов требуется трансфер.",
    ("vladivostok", "vvo-family-nature", "botanical-garden-vvo", "sportivnaya-harbour"):
        "Ботанический сад и Спортивная гавань находятся далеко друг от друга.",
    ("volgograd", "vlg-south", "volgograd-elevator", "old-sarepta"):
        "От элеватора до Старой Сарепты нужен дальний переезд.",
}


def detect_long_transfers(catalogs: Iterable[CityCatalog]) -> set[TransferKey]:
    """Calculate current legs; never infer a service from straight-line distance."""
    found: set[TransferKey] = set()
    for catalog in catalogs:
        places = {place.slug: place for place in catalog.places}
        for route in catalog.routes:
            ordered = tuple(places[slug] for slug in route.place_slugs if slug in places)
            for start, finish, _ in route_geography(ordered).long_legs:
                found.add((catalog.slug, route.slug, start, finish))
    return found


def audit_reviewed_transfers(
    catalogs: Iterable[CityCatalog],
) -> tuple[tuple[TransferKey, ...], tuple[TransferKey, ...]]:
    """Return unreviewed legs and stale registry entries, in stable order."""
    actual = detect_long_transfers(catalogs)
    return (
        tuple(sorted(actual - REVIEWED_TRANSFERS.keys())),
        tuple(sorted(REVIEWED_TRANSFERS.keys() - actual)),
    )


def transfer_notes(city_slug: str, route_slug: str) -> tuple[str, ...]:
    return tuple(
        note for (city, route, _start, _finish), note in REVIEWED_TRANSFERS.items()
        if city == city_slug and route == route_slug
    )


def route_requires_transport(city_slug: str, route_slug: str) -> bool:
    return any(
        city == city_slug and route == route_slug
        for city, route, _start, _finish in REVIEWED_TRANSFERS
    )


def verify_registered_transfers() -> None:
    missing, obsolete = audit_reviewed_transfers(list_catalogs())
    if missing or obsolete:
        raise RuntimeError(
            f"Long-distance editorial route boundaries need review: "
            f"unreviewed={missing}; obsolete={obsolete}"
        )

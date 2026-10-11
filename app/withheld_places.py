"""Visit recommendations deferred due to current evidence of uncertain access.

A withheld attraction is not necessarily demolished or permanently closed.
Reinstate only after a dated operator/municipal opening announcement or
independent evidence that it has been commissioned and can be visited.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from app.catalog import CityCatalog, list_catalogs


@dataclass(frozen=True, slots=True)
class WithheldPlace:
    city_slug: str
    place_slug: str
    title: str
    reason: str
    map_url: str
    map_last_modified: str
    reviewed_on: str
    context_url: str


WITHHELD_PLACES = (
    WithheldPlace(
        city_slug="nalchik",
        place_slug="nalchik-osm-way-234973881",
        title="Дворец театров",
        reason=(
            "На 11.10.2026 нет подтверждения ввода в эксплуатацию или приёма "
            "посетителей; в OSM у объекта construction=yes по состоянию "
            "на 15.03.2026. Это сигнал строительства, НЕ доказательство сноса."
        ),
        map_url="https://www.openstreetmap.org/way/234973881",
        map_last_modified="2026-03-15T20:33:03Z",
        reviewed_on="2026-10-11",
        context_url="https://www.gazprommap.ru/official/news/detail/item/2798/",
    ),
)


def check_withheld(catalogs: tuple[CityCatalog, ...] | None = None) -> tuple[str, ...]:
    active = list_catalogs() if catalogs is None else catalogs
    forbidden = {(p.city_slug, p.place_slug) for p in WITHHELD_PLACES}
    findings = []
    for city in active:
        for place in city.places:
            if (city.slug, place.slug) in forbidden:
                findings.append(
                    f"{city.slug}/{place.slug}: unverified construction site active"
                )
        for route in city.routes:
            if any((city.slug, slug) in forbidden for slug in route.place_slugs):
                findings.append(
                    f"{city.slug}/{route.slug}: route contains withheld site"
                )
    return tuple(findings)


def withheld_metadata() -> list[dict]:
    return [asdict(record) for record in WITHHELD_PLACES]

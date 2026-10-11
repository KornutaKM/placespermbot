"""Evidence-led inventory: source dates are not proof of current opening.

No network access in production. A removed object's slug stays reserved
forever so that old backups cannot silently resurrect it into a live route.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from urllib.parse import urlparse

from app.catalog import CityCatalog, list_catalogs


@dataclass(frozen=True, slots=True)
class Retirement:
    city_slug: str
    place_slug: str
    title: str
    event_date: str
    recorded_on: str
    reason: str
    sources: tuple[str, ...]


RETIRED = (
    Retirement(
        "perm", "perm-gates", "Пермские ворота", "2024-06-19",
        "2026-10-11",
        "Арт-объект демонтирован в июне 2024 года: посещение невозможно.",
        (
            "https://www.kommersant.ru/gallery/6788178",
            "https://perm.rbc.ru/perm/freenews/66732aed9a79474d788500d5",
            "https://vesti-perm.ru/pages/55f5e74d0df94bf79b346cde06084628",
        ),
    ),
)


@dataclass(frozen=True, slots=True)
class PublishedObservation:
    city_slug: str
    place_slug: str
    reported_on: str
    statement: str
    source_url: str


# An observation attests a past date only, NOT current hours or accessibility.
OBSERVATIONS = (
    PublishedObservation(
        "perm", "perm-art-gallery", "2026-04-02",
        "Новый корпус галереи на Заводе Шпагина открылся для посетителей.",
        "https://permkrai.er.ru/activity/news/"
        "v-permi-sostoyalos-torzhestvennoe-otkrytie-"
        "novoj-hudozhestvennoj-galerei-na-zavode-shpagina",
    ),
)


def source_type(url: str) -> str:
    host = (urlparse(url).hostname or "").casefold()
    if host == "www.openstreetmap.org":
        return "community_osm"
    if host == "www.wikidata.org":
        return "community_wikidata"
    return "editorial_or_institutional"


def check_retirements(catalogs: tuple[CityCatalog, ...]) -> tuple[str, ...]:
    forbidden = {(entry.city_slug, entry.place_slug) for entry in RETIRED}
    problems = []
    for city in catalogs:
        for place in city.places:
            if (city.slug, place.slug) in forbidden:
                problems.append(f"{city.slug}/{place.slug}: removed object is active")
        for route in city.routes:
            for slug in route.place_slugs:
                if (city.slug, slug) in forbidden:
                    problems.append(f"{city.slug}/{route.slug}: visits removed {slug}")
    return tuple(problems)


def build_inventory(
    catalogs: tuple[CityCatalog, ...] | None = None,
    *, as_of: date | None = None,
) -> dict:
    """Cover every point. Unknown must never be promoted to 'verified'."""
    catalogs = list_catalogs() if catalogs is None else catalogs
    today = datetime.now(UTC).date() if as_of is None else as_of
    observations = {(o.city_slug, o.place_slug): o for o in OBSERVATIONS}
    source_counts = {
        "community_osm": 0, "community_wikidata": 0,
        "editorial_or_institutional": 0,
    }
    places = []
    cities = []
    for city in catalogs:
        city_places = []
        for place in city.places:
            kind = source_type(place.source.url)
            source_counts[kind] += 1
            age = (today - place.source.checked_at).days
            observation = observations.get((city.slug, place.slug))
            priority = (
                "high" if kind != "editorial_or_institutional"
                or place.category in {"museums", "family"} or age >= 180
                else "standard"
            )
            item = {
                "city_slug": city.slug,
                "city_name": city.name,
                "place_slug": place.slug,
                "title": place.title,
                "category": place.category,
                "source_type": kind,
                "source_url": place.source.url,
                "source_recorded_on": place.source.checked_at.isoformat(),
                "source_age_days": age,
                "review_priority": priority,
                "review_status": "requires_current_independent_confirmation",
                "past_published_observation": (
                    asdict(observation) if observation else None
                ),
            }
            places.append(item)
            city_places.append(item)
        cities.append({
            "slug": city.slug,
            "name": city.name,
            "total": len(city_places),
            "high_priority": sum(
                p["review_priority"] == "high" for p in city_places
            ),
            "not_verified_now": len(city_places),
            "community_map_entries": sum(
                p["source_type"].startswith("community_") for p in city_places
            ),
        })
    return {
        "audit_date": today.isoformat(),
        "scope": "All active cities and attractions; source provenance "
                 "inventory ONLY, not on-site or independent current verification",
        "cities_count": len(cities),
        "active_places_count": len(places),
        "not_verified_now": len(places),
        "historically_removed_count": len(RETIRED),
        "documented_past_observations": sum(
            p["past_published_observation"] is not None for p in places
        ),
        "source_types": source_counts,
        "blocking_findings": list(check_retirements(catalogs)),
        "retired": [asdict(item) for item in RETIRED],
        "cities": cities,
        "places": places,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Инвентаризация актуальности достопримечательностей",
        "",
        f"Дата: {report['audit_date']}.",
        "",
        "Наличие URL и дата источника не подтверждают физическое существование "
        "или часы работы достопримечательности сегодня.",
        "",
        f"Городов: **{report['cities_count']}**; "
        f"активных карточек: **{report['active_places_count']}**; "
        f"без индивидуального текущего подтверждения: "
        f"**{report['not_verified_now']}**.",
        "",
        f"Подтверждённо исчезнувших объектов исключено: "
        f"**{report['historically_removed_count']}**.",
        "",
        "## По городам",
        "",
        "| Город | Карточек | Высокий приоритет проверки |",
        "|---|---:|---:|",
    ]
    for city in report["cities"]:
        lines.append(
            f"| {city['name']} | {city['total']} | {city['high_priority']} |"
        )
    lines.extend([
        "",
        "## Исключённые объекты с документальным подтверждением",
        "",
    ])
    for item in report["retired"]:
        lines.append(
            f"- {item['title']} ({item['city_slug']}/{item['place_slug']}), "
            f"{item['event_date']}: {item['reason']} "
            + ", ".join(item["sources"])
        )
    lines.extend([
        "",
        "Подробный построчный реестр источников доступен в JSON-артефакте CI.",
        "Весь список требует последовательной независимой проверки; "
        "результат нельзя считать подтверждением работы всех мест.",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = build_inventory()
    print(
        json.dumps(report, ensure_ascii=False, indent=2)
        if args.format == "json" else render_markdown(report)
    )
    if args.check and report["blocking_findings"]:
        raise SystemExit("\n".join(report["blocking_findings"]))


if __name__ == "__main__":
    main()

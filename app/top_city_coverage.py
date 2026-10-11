"""Top 100 population-ranked cities: target coverage, not fabricated guides.

Ranking snapshot: permanent resident population within city boundaries on
2025-01-01. Source: https://www.mojgorod.ru/cities/pop2025_1.html and
the 500k and 100k continuation tables (`_2.html`, `_3.html`).

Only registered, validated CityManifest entries count as operational guides.
Names lacking a catalog are directory entries, not selectable cities.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from app.city_manifest import list_city_manifests
from app.data.osm_seed_2026 import OSM_SEED_CITIES

RANKING_DATE = "2025-01-01"
RANKING_SOURCES = (
    "https://www.mojgorod.ru/cities/pop2025_1.html",
    "https://www.mojgorod.ru/cities/pop2025_2.html",
    "https://www.mojgorod.ru/cities/pop2025_3.html",
)

TOP_100_NAMES = tuple(line.strip() for line in """
Москва
Санкт-Петербург
Новосибирск
Екатеринбург
Казань
Красноярск
Нижний Новгород
Челябинск
Уфа
Краснодар
Самара
Ростов-на-Дону
Омск
Воронеж
Пермь
Волгоград
Саратов
Тюмень
Тольятти
Махачкала
Барнаул
Ижевск
Хабаровск
Ульяновск
Иркутск
Владивосток
Ярославль
Ставрополь
Набережные Челны
Томск
Балашиха
Кемерово
Оренбург
Новокузнецк
Рязань
Севастополь
Чебоксары
Калининград
Пенза
Липецк
Киров
Астрахань
Тула
Сочи
Улан-Удэ
Курск
Сургут
Тверь
Магнитогорск
Грозный
Якутск
Брянск
Иваново
Владимир
Чита
Симферополь
Нижний Тагил
Калуга
Белгород
Подольск
Волжский
Вологда
Смоленск
Саранск
Курган
Череповец
Архангельск
Владикавказ
Нижневартовск
Орёл
Йошкар-Ола
Стерлитамак
Мытищи
Кострома
Мурманск
Новороссийск
Химки
Тамбов
Нальчик
Нижнекамск
Таганрог
Благовещенск
Люберцы
Петрозаводск
Комсомольск-на-Амуре
Королёв
Великий Новгород
Энгельс
Братск
Шахты
Сыктывкар
Ангарск
Старый Оскол
Дзержинск
Красногорск
Одинцово
Псков
Орск
Армавир
Абакан
""".strip().splitlines())

# Reserved city slugs for yet-to-be-built guides. Keep stable when they become
# full catalogs, so population ranking metadata never resets user city identity.
RESERVED_SLUGS = {
    "Тольятти": "tolyatti",
    "Махачкала": "makhachkala",
    "Барнаул": "barnaul",
    "Ижевск": "izhevsk",
    "Ульяновск": "ulyanovsk",
    "Ставрополь": "stavropol",
    "Набережные Челны": "naberezhnye-chelny",
    "Балашиха": "balashikha",
    "Кемерово": "kemerovo",
    "Оренбург": "orenburg",
    "Новокузнецк": "novokuznetsk",
    "Севастополь": "sevastopol",
    "Чебоксары": "cheboksary",
    "Липецк": "lipetsk",
    "Киров": "kirov",
    "Сургут": "surgut",
    "Тверь": "tver",
    "Магнитогорск": "magnitogorsk",
    "Грозный": "grozny",
    "Якутск": "yakutsk",
    "Брянск": "bryansk",
    "Иваново": "ivanovo",
    "Чита": "chita",
    "Симферополь": "simferopol",
    "Нижний Тагил": "nizhny-tagil",
    "Калуга": "kaluga",
    "Белгород": "belgorod",
    "Подольск": "podolsk",
    "Волжский": "volzhsky",
    "Смоленск": "smolensk",
    "Саранск": "saransk",
    "Курган": "kurgan",
    "Череповец": "cherepovets",
    "Владикавказ": "vladikavkaz",
    "Нижневартовск": "nizhnevartovsk",
    "Орёл": "oryol",
    "Стерлитамак": "sterlitamak",
    "Мытищи": "mytishchi",
    "Новороссийск": "novorossiysk",
    "Химки": "khimki",
    "Тамбов": "tambov",
    "Нальчик": "nalchik",
    "Нижнекамск": "nizhnekamsk",
    "Таганрог": "taganrog",
    "Благовещенск": "blagoveshchensk",
    "Люберцы": "lyubertsy",
    "Комсомольск-на-Амуре": "komsomolsk-on-amur",
    "Королёв": "korolyov",
    "Энгельс": "engels",
    "Братск": "bratsk",
    "Шахты": "shakhty",
    "Ангарск": "angarsk",
    "Старый Оскол": "stary-oskol",
    "Дзержинск": "dzerzhinsk",
    "Красногорск": "krasnogorsk",
    "Одинцово": "odintsovo",
    "Орск": "orsk",
    "Армавир": "armavir",
    "Абакан": "abakan",
}


@dataclass(frozen=True, slots=True)
class TopCity:
    rank: int
    name: str
    slug: str
    guide_available: bool
    guide_status: str


def top_city_coverage() -> tuple[TopCity, ...]:
    """Consistent view of the ranked target and live manifest-backed coverage."""
    active = {city.name: city.slug for city in list_city_manifests()}
    map_seeds = {city.slug for city in OSM_SEED_CITIES}
    result: list[TopCity] = []
    for rank, name in enumerate(TOP_100_NAMES, start=1):
        known_slug = RESERVED_SLUGS.get(name)
        registered_slug = active.get(name)
        if known_slug and registered_slug and known_slug != registered_slug:
            raise RuntimeError(f"Reserved slug mismatch for {name}")
        slug = registered_slug or known_slug
        if not slug:
            raise RuntimeError(f"Top-100 city lacks canonical slug: {name}")
        result.append(TopCity(
            rank, name, slug, registered_slug is not None,
            "map_seed" if slug in map_seeds else (
                "editorial" if registered_slug is not None else "pending"
            ),
        ))
    if len(result) != 100 or len({c.name for c in result}) != 100:
        raise RuntimeError("Invalid top-100 population ranking")
    if len({c.slug for c in result}) != 100:
        raise RuntimeError("Duplicate slug in top-100 population ranking")
    return tuple(result)


def coverage_summary() -> dict:
    ranked = top_city_coverage()
    covered = sum(city.guide_available for city in ranked)
    editorial = sum(city.guide_status == "editorial" for city in ranked)
    seeded = sum(city.guide_status == "map_seed" for city in ranked)
    return {
        "ranking_date": RANKING_DATE,
        "ranking_sources": list(RANKING_SOURCES),
        "target_count": len(ranked),
        "ready_count": covered,
        "editorial_count": editorial,
        "map_seed_count": seeded,
        "pending_count": len(ranked) - covered,
        "catalog_city_count": len(list_city_manifests()),
        "cities": [asdict(city) for city in ranked],
    }


def check_coverage_registry() -> None:
    if len(TOP_100_NAMES) != 100 or len(set(TOP_100_NAMES)) != 100:
        raise RuntimeError("Ranking must contain 100 unique city names")
    if not set(RESERVED_SLUGS).issubset(TOP_100_NAMES):
        raise RuntimeError("Reserved slug is not present in top 100")
    top_city_coverage()


if __name__ == "__main__":
    check_coverage_registry()
    summary = coverage_summary()
    print(
        f"top-100: target={summary['target_count']} "
        f"ready={summary['ready_count']} pending={summary['pending_count']} "
        f"catalogs={summary['catalog_city_count']}"
    )

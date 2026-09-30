from datetime import date

from app.domain import Place, PlaceSource, RoutePlan

CITY_SLUG = "perm"
CITY_NAME = "Пермь"
SOURCE_CHECKED_AT = date(2026, 9, 30)

SALTY_EARS_SOURCE = PlaceSource(
    name="Пермь монументальная — Пермяк — солёные уши",
    url="https://monuments.permartmuseum.ru/object/115",
    checked_at=SOURCE_CHECKED_AT,
)
PERM_BEAR_SOURCE = PlaceSource(
    name="Культура.РФ — гид по Перми",
    url="https://www.culture.ru/materials/257798/gid-po-permi",
    checked_at=SOURCE_CHECKED_AT,
)
PERM_MUSEUM_SOURCE = PlaceSource(
    name="Пермский краеведческий музей",
    url="https://museumperm.ru/branches",
    checked_at=SOURCE_CHECKED_AT,
)
PERM_GATES_SOURCE = PlaceSource(
    name="Пермь монументальная — Пермские ворота",
    url="https://monuments.permartmuseum.ru/object/28",
    checked_at=SOURCE_CHECKED_AT,
)
FRONT_REAR_SOURCE = PlaceSource(
    name="Пермь монументальная — Героям фронта и тыла",
    url="https://monuments.permartmuseum.ru/object/56",
    checked_at=SOURCE_CHECKED_AT,
)
GORKY_PARK_SOURCE = PlaceSource(
    name="Парк Горького в Перми",
    url="https://www.parkperm.ru/about-park/",
    checked_at=SOURCE_CHECKED_AT,
)
THEATRE_SOURCE = PlaceSource(
    name="Пермский академический Театр-Театр",
    url="https://teatr-teatr.com/about/teatr-segodnya/",
    checked_at=SOURCE_CHECKED_AT,
)

CATEGORY_LABELS: dict[str, str] = {
    "sights": "🏛 Достопримечательности",
    "unusual": "✨ Необычные места",
    "museums": "🖼 Музеи и культура",
    "parks": "🌿 Парки и прогулки",
    "family": "👨‍👩‍👧 С детьми",
    "free": "💸 Бесплатно",
}

PLACES: tuple[Place, ...] = (
    Place(
        slug="permyak-salty-ears",
        title="Пермяк — солёные уши",
        category="unusual",
        summary=(
            "Городская скульптурная композиция и один из самых узнаваемых "
            "неформальных символов Перми."
        ),
        emoji="👂",
        district="Ленинский район",
        visit_minutes=20,
        is_free=True,
        latitude=58.009736,
        longitude=56.239636,
        source=SALTY_EARS_SOURCE,
        tags=("городское искусство", "символ города", "центр", "бесплатно"),
    ),
    Place(
        slug="perm-bear",
        title="Легенда о пермском медведе",
        category="unusual",
        summary=(
            "Бронзовая скульптура медведя в центре города, связанная с "
            "официальной символикой Перми."
        ),
        emoji="🐻",
        district="Ленинский район",
        visit_minutes=20,
        is_free=True,
        latitude=58.010731,
        longitude=56.237605,
        source=PERM_BEAR_SOURCE,
        tags=("городское искусство", "символ города", "центр", "бесплатно"),
    ),
    Place(
        slug="meshkov-house",
        title="Дом Мешкова",
        category="museums",
        summary=(
            "Исторический особняк на Монастырской улице и главное здание "
            "Пермского краеведческого музея."
        ),
        emoji="🏛",
        district="Ленинский район",
        visit_minutes=90,
        is_free=False,
        latitude=58.018788,
        longitude=56.246631,
        source=PERM_MUSEUM_SOURCE,
        tags=("музей", "история", "архитектура", "центр"),
    ),
    Place(
        slug="perm-antiquities-museum",
        title="Музей пермских древностей",
        category="museums",
        summary=(
            "Естественно-научный музей о геологической и палеонтологической "
            "истории региона и Пермском периоде."
        ),
        emoji="🦣",
        district="Ленинский район",
        visit_minutes=90,
        is_free=False,
        latitude=58.014121,
        longitude=56.245460,
        source=PERM_MUSEUM_SOURCE,
        tags=("музей", "палеонтология", "пермский период", "с детьми"),
    ),
    Place(
        slug="perm-gates",
        title="Пермские ворота",
        category="unusual",
        summary=(
            "Паблик-арт объект Николая Полисского из еловых брёвен в "
            "саду имени 250-летия Перми."
        ),
        emoji="🪵",
        district="Дзержинский район",
        visit_minutes=30,
        is_free=True,
        latitude=58.004528,
        longitude=56.193416,
        source=PERM_GATES_SOURCE,
        tags=("современное искусство", "городское искусство", "прогулка", "бесплатно"),
    ),
    Place(
        slug="front-and-rear-monument",
        title="Монумент «Героям фронта и тыла»",
        category="sights",
        summary=(
            "Монументальная композиция 1985 года в центре городской "
            "эспланады."
        ),
        emoji="🗿",
        district="Ленинский район",
        visit_minutes=25,
        is_free=True,
        latitude=58.009168,
        longitude=56.223028,
        source=FRONT_REAR_SOURCE,
        tags=("история", "мемориал", "центр", "бесплатно"),
    ),
    Place(
        slug="gorky-park-perm",
        title="Парк Горького",
        category="parks",
        summary=(
            "Исторический городской парк в центре Перми с прогулочными "
            "аллеями и архитектурной ротондой."
        ),
        emoji="🌳",
        district="Свердловский район",
        visit_minutes=90,
        is_free=True,
        latitude=58.005000,
        longitude=56.248100,
        source=GORKY_PARK_SOURCE,
        tags=("парк", "прогулка", "с детьми", "центр"),
    ),
    Place(
        slug="theatre-theatre",
        title="Пермский академический Театр-Театр",
        category="sights",
        summary=(
            "Крупный репертуарный театр на городской эспланаде и заметный "
            "объект советского модернизма."
        ),
        emoji="🎭",
        district="Ленинский район",
        visit_minutes=30,
        is_free=True,
        latitude=58.008139,
        longitude=56.216121,
        source=THEATRE_SOURCE,
        tags=("театр", "архитектура", "культура", "центр"),
    ),,
    Place(
        slug="perm-esplanade",
        title="Пермская эспланада",
        category="parks",
        summary="Главное открытое общественное пространство центра Перми между Театром-Театром и городской администрацией.",
        emoji="🌆",
        district="Ленинский район",
        visit_minutes=60,
        is_free=True,
        latitude=58.0100,
        longitude=56.2290,
        source=THEATRE_SOURCE,
        tags=("прогулка", "центр", "городская среда", "бесплатно"),
    ),
    Place(
        slug="kama-embankment-perm",
        title="Набережная Камы",
        category="parks",
        summary="Прогулочная набережная вдоль Камы у исторического центра Перми.",
        emoji="🌊",
        district="Ленинский район",
        visit_minutes=90,
        is_free=True,
        latitude=58.0210,
        longitude=56.2430,
        source=PERM_MUSEUM_SOURCE,
        tags=("набережная", "прогулка", "виды", "бесплатно"),
    ),
    Place(
        slug="perm-art-gallery",
        title="Пермская художественная галерея",
        category="museums",
        summary="Крупное художественное собрание региона, известное в том числе коллекцией пермской деревянной скульптуры.",
        emoji="🖼",
        district="Ленинский район",
        visit_minutes=120,
        is_free=False,
        latitude=58.0165,
        longitude=56.2435,
        source=PERM_MUSEUM_SOURCE,
        tags=("музей", "искусство", "деревянная скульптура"),
    ),
    Place(
        slug="razgulyai-perm",
        title="Разгуляй",
        category="sights",
        summary="Историческая часть Перми с сохранившейся городской застройкой и тихими улицами.",
        emoji="🏘",
        district="Ленинский район",
        visit_minutes=75,
        is_free=True,
        latitude=58.0250,
        longitude=56.2530,
        source=PERM_MUSEUM_SOURCE,
        tags=("история", "архитектура", "прогулка", "бесплатно"),
    )
)

ROUTES: tuple[RoutePlan, ...] = (
    RoutePlan(
        slug="perm-symbols",
        title="Символы Перми",
        summary=(
            "Короткая прогулка через городской парк к двум самым "
            "узнаваемым уличным символам Перми."
        ),
        duration_minutes=180,
        distance_km=0.9,
        place_slugs=(
            "gorky-park-perm",
            "permyak-salty-ears",
            "perm-bear",
        ),
    ),
    RoutePlan(
        slug="perm-history-and-esplanade",
        title="История и эспланада",
        summary=(
            "Маршрут от музейного квартала к главным пространствам "
            "городской эспланады."
        ),
        duration_minutes=270,
        distance_km=2.4,
        place_slugs=(
            "meshkov-house",
            "perm-antiquities-museum",
            "front-and-rear-monument",
            "theatre-theatre",
        ),
    ),,
    RoutePlan(
        slug="perm-kama-walk",
        title="Пермь и Кама",
        summary="Исторический центр, музейный квартал и прогулка к Каме.",
        duration_minutes=270,
        distance_km=3.0,
        place_slugs=("razgulyai-perm", "meshkov-house", "kama-embankment-perm"),
    ),
    RoutePlan(
        slug="perm-art-city",
        title="Искусство и город",
        summary="Художественная галерея, городские арт-объекты и центральная эспланада.",
        duration_minutes=300,
        distance_km=4.0,
        place_slugs=("perm-art-gallery", "permyak-salty-ears", "front-and-rear-monument", "perm-esplanade"),
    )
)

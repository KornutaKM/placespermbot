from datetime import date

from app.domain import Place, PlaceSource, RoutePlan

CITY_SLUG = "perm"
CITY_NAME = "Пермь"
SOURCE_CHECKED_AT = date(2026, 9, 30)
NEW_SOURCE_CHECKED_AT = date(2026, 10, 1)

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
DIORAMA_SOURCE = PlaceSource(
    name="Пермский краеведческий музей — Музей-диорама",
    url="https://museumperm.ru/branch/diorama",
    checked_at=SOURCE_CHECKED_AT,
)
SLAVYANOV_SOURCE = PlaceSource(
    name="Пермский краеведческий музей — Дом-музей Николая Славянова",
    url="https://museumperm.ru/branch/domslavyanova",
    checked_at=SOURCE_CHECKED_AT,
)
THEATRE_SOURCE = PlaceSource(
    name="Пермский академический Театр-Театр",
    url="https://teatr-teatr.com/about/teatr-segodnya/",
    checked_at=SOURCE_CHECKED_AT,
)
ZOO_SOURCE = PlaceSource(
    name="Пермский зоопарк — информация посетителям",
    url="https://zoo.perm.ru/for-visitors/information",
    checked_at=NEW_SOURCE_CHECKED_AT,
)
PLANETARIUM_SOURCE = PlaceSource(
    name="Пермский планетарий",
    url="https://planetarium.perm.ru/o-nas/dostupnaja-sreda/",
    checked_at=NEW_SOURCE_CHECKED_AT,
)
CHILDREN_MUSEUM_SOURCE = PlaceSource(
    name="Пермский краеведческий музей — Детский музейный центр",
    url="https://museumperm.ru/branch/kids",
    checked_at=NEW_SOURCE_CHECKED_AT,
)
PERMM_SOURCE = PlaceSource(
    name="Музей современного искусства PERMM",
    url="https://permm.ru/~/afisha",
    checked_at=NEW_SOURCE_CHECKED_AT,
)
OPERA_SOURCE = PlaceSource(
    name="Пермский театр оперы и балета — контакты",
    url="https://permopera.ru/about/contacts/",
    checked_at=NEW_SOURCE_CHECKED_AT,
)
ART_GALLERY_SOURCE = PlaceSource(
    name="Пермская государственная художественная галерея — билеты",
    url="https://tickets.permartmuseum.ru/place/2",
    checked_at=NEW_SOURCE_CHECKED_AT,
)
ESPLANADE_SOURCE = PlaceSource(
    name="Администрация Перми — зелёный фонд",
    url="https://www.gorodperm.ru/actions/ecology/citynature/greenfund/",
    checked_at=NEW_SOURCE_CHECKED_AT,
)
KAMA_EMBANKMENT_SOURCE = PlaceSource(
    name="Пермь. Три столетия — река Кама",
    url="https://book.gorodperm.ru/kama",
    checked_at=NEW_SOURCE_CHECKED_AT,
)
RAZGULYAI_SOURCE = PlaceSource(
    name="Пермь. Три столетия — история города",
    url="https://book.gorodperm.ru/history",
    checked_at=NEW_SOURCE_CHECKED_AT,
)

EDITORIAL_CHECKED_AT = date(2026, 10, 8)

PERM_FILIALS = PlaceSource(
    name="Пермский краеведческий музей — актуальные адреса городских филиалов",
    url="https://museumperm.ru/branches",
    checked_at=EDITORIAL_CHECKED_AT,
)

PERM_UNDERGROUND = PlaceSource(
    name="Пермский краеведческий музей — Подпольная типография",
    url="https://museumperm.ru/branch/podpolka",
    checked_at=EDITORIAL_CHECKED_AT,
)

PERM_VISIT = PlaceSource(
    name="Пермский краеведческий музей — актуальный режим объектов",
    url="https://museumperm.ru/visit",
    checked_at=EDITORIAL_CHECKED_AT,
)

PERM_CITY = PlaceSource(
    name="Администрация Перми — городские зелёные территории",
    url="https://www.gorodperm.ru/actions/ecology/citynature/greenfund/",
    checked_at=EDITORIAL_CHECKED_AT,
)

PERM_HISTORY = PlaceSource(
    name="«Пермь. Три столетия» — история города",
    url="https://book.gorodperm.ru/history",
    checked_at=EDITORIAL_CHECKED_AT,
)

PERM_KAMA = PlaceSource(
    name="«Пермь. Три столетия» — город и Кама",
    url="https://book.gorodperm.ru/kama",
    checked_at=EDITORIAL_CHECKED_AT,
)

PERM_ART = PlaceSource(
    name="Пермская художественная галерея — музейная информация",
    url="https://permartmuseum.ru/",
    checked_at=EDITORIAL_CHECKED_AT,
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
    ),
    Place(
        slug="perm-esplanade",
        title="Пермская эспланада",
        category="parks",
        summary=(
            "Главное открытое общественное пространство центра Перми "
            "между Театром-Театром и городской администрацией."
        ),
        emoji="🌆",
        district="Ленинский район",
        visit_minutes=60,
        is_free=True,
        latitude=58.0100,
        longitude=56.2290,
        source=ESPLANADE_SOURCE,
        tags=("прогулка", "центр", "городская среда", "бесплатно"),
    ),
    Place(
        slug="kama-embankment-perm",
        title="Набережная Камы",
        category="parks",
        summary=(
            "Обновлённый городской променад вдоль Камы с амфитеатром, "
            "зонами отдыха и панорамой реки."
        ),
        emoji="🌊",
        district="Ленинский район",
        visit_minutes=90,
        is_free=True,
        latitude=58.0210,
        longitude=56.2430,
        source=KAMA_EMBANKMENT_SOURCE,
        tags=("набережная", "прогулка", "виды", "бесплатно"),
    ),
    Place(
        slug="perm-art-gallery",
        title="Пермская художественная галерея",
        category="museums",
        summary=(
            "Главное художественное собрание региона в новом музейном "
            "корпусе на территории Завода Шпагина."
        ),
        emoji="🖼",
        district="Ленинский район",
        visit_minutes=120,
        is_free=False,
        latitude=58.02123,
        longitude=56.25845,
        source=ART_GALLERY_SOURCE,
        tags=("музей", "искусство", "деревянная скульптура"),
    ),
    Place(
        slug="perm-diorama",
        title="Музей-диорама",
        category="museums",
        summary="Музей на горе Вышка об истории Мотовилихи, заводского поселения и событиях 1905 года.",
        emoji="🏭",
        district="Мотовилихинский район",
        visit_minutes=90,
        is_free=False,
        latitude=58.0411,
        longitude=56.3206,
        source=DIORAMA_SOURCE,
        tags=("музей", "история", "промышленность", "мотовилиха"),
    ),
    Place(
        slug="slavyanov-house",
        title="Дом-музей Н. Г. Славянова",
        category="museums",
        summary="Мемориальный музей инженера Николая Славянова, связанный с историей электродуговой сварки и Мотовилихи.",
        emoji="⚙️",
        district="Мотовилихинский район",
        visit_minutes=75,
        is_free=False,
        latitude=58.0348,
        longitude=56.3089,
        source=SLAVYANOV_SOURCE,
        tags=("музей", "инженерия", "промышленность", "история"),
    ),
    Place(
        slug="razgulyai-perm",
        title="Разгуляй",
        category="sights",
        summary=(
            "Историческая часть Перми с сохранившейся городской "
            "застройкой и тихими улицами."
        ),
        emoji="🏘",
        district="Ленинский район",
        visit_minutes=75,
        is_free=True,
        latitude=58.0250,
        longitude=56.2530,
        source=RAZGULYAI_SOURCE,
        tags=("история", "архитектура", "прогулка", "бесплатно"),
    ),
    Place(
        slug="perm-zoo",
        title="Пермский зоопарк",
        category="family",
        summary=(
            "Новый природно-ландшафтный комплекс на Свиязева с крупными "
            "экспозиционными зонами и программами для семейной аудитории."
        ),
        emoji="🦒",
        district="Индустриальный район",
        visit_minutes=180,
        is_free=False,
        latitude=57.9610,
        longitude=56.1786,
        source=ZOO_SOURCE,
        tags=("с детьми", "животные", "зоопарк", "природа"),
    ),
    Place(
        slug="perm-planetarium",
        title="Пермский планетарий",
        category="family",
        summary=(
            "Городской планетарий с программами об астрономии и "
            "космонавтике, включая наблюдения в телескоп."
        ),
        emoji="🪐",
        district="Мотовилихинский район",
        visit_minutes=90,
        is_free=False,
        latitude=58.019255,
        longitude=56.271350,
        source=PLANETARIUM_SOURCE,
        tags=("с детьми", "астрономия", "космос", "наука"),
    ),
    Place(
        slug="perm-childrens-museum-center",
        title="Детский музейный центр",
        category="family",
        summary=(
            "Интерактивное выставочно-игровое пространство Пермского "
            "краеведческого музея на территории Завода Шпагина."
        ),
        emoji="🧩",
        district="Ленинский район",
        visit_minutes=90,
        is_free=False,
        latitude=58.018712,
        longitude=56.252701,
        source=CHILDREN_MUSEUM_SOURCE,
        tags=("с детьми", "музей", "интерактив", "творчество"),
    ),
    Place(
        slug="permm",
        title="Музей современного искусства PERMM",
        category="museums",
        summary=(
            "Музей современного искусства с постоянной коллекцией, "
            "временными выставками и образовательными программами."
        ),
        emoji="🎨",
        district="Дзержинский район",
        visit_minutes=120,
        is_free=False,
        latitude=58.0122,
        longitude=56.2103,
        source=PERMM_SOURCE,
        tags=("музей", "современное искусство", "выставки", "культура"),
    ),
    Place(
        slug="perm-opera",
        title="Пермский театр оперы и балета",
        category="sights",
        summary=(
            "Историческая театральная сцена имени П. И. Чайковского и "
            "один из ключевых культурных символов города."
        ),
        emoji="🎼",
        district="Ленинский район",
        visit_minutes=45,
        is_free=False,
        latitude=58.01583,
        longitude=56.24611,
        source=OPERA_SOURCE,
        tags=("театр", "опера", "балет", "архитектура", "культура"),
    ),
    Place(
        "perm-underground-printshop",
        "Дом-музей «Подпольная типография»",
        "museums",
        "Музей рабочих-подпольщиков 1906 года на Монастырской, 142; экскурсии по предварительной заявке и подтверждению музея.",
        "📰",
        "Монастырская, 142",
        100,
        False,
        58.0091,
        56.1972,
        PERM_UNDERGROUND,
        ("музей", "история", "типография", "с детьми"),
    ),
    Place(
        "perm-meshkov-facade",
        "Фасад Дома Мешкова",
        "sights",
        "Исторический особняк Монастырской, 11 с музейным фасадом; наружный осмотр свободен, залы по билету.",
        "🏛",
        "Монастырская, 11",
        45,
        True,
        58.0189,
        56.2464,
        PERM_FILIALS,
        ("архитектура", "усадьба", "история", "с детьми", "бесплатно"),
    ),
    Place(
        "perm-museum-ancient-family",
        "Палеонтологическая экспозиция для семьи",
        "family",
        "Семейная программа Музея пермских древностей на Сибирской, 15; зал на четвёртом этаже, доступность для маломобильных посетителей ограничена.",
        "🦣",
        "Сибирская, 15",
        100,
        False,
        58.0141,
        56.2456,
        PERM_VISIT,
        ("музей", "палеонтология", "наука", "с детьми"),
    ),
    Place(
        "perm-theatre-square",
        "Театральный сквер",
        "parks",
        "Открытая площадь и аллеи около Пермского театра оперы и балета.",
        "🌳",
        "Театральный сквер",
        80,
        True,
        58.0153,
        56.245,
        PERM_CITY,
        ("сквер", "театр", "прогулка", "с детьми", "бесплатно"),
    ),
    Place(
        "perm-peter-paul-cathedral",
        "Петропавловский собор — внешний осмотр",
        "sights",
        "Исторический собор Петровской слободы; внутренний доступ и богослужения уточняйте отдельно.",
        "⛪",
        "Разгуляй",
        55,
        True,
        58.0265,
        56.2612,
        PERM_HISTORY,
        ("собор", "история", "архитектура", "бесплатно"),
    ),
    Place(
        "perm-gorky-rotunda",
        "Ротонда парка Горького",
        "unusual",
        "Историческая деревянная ротонда на прогулочных аллеях городского парка.",
        "🏛",
        "Парк Горького",
        45,
        True,
        58.0056,
        56.2485,
        PERM_CITY,
        ("ротонда", "архитектура", "с детьми", "бесплатно"),
    ),
    Place(
        "perm-river-scenic",
        "Видовая прогулка у Камы",
        "parks",
        "Открытый пешеходный участок набережной у центра с видами на Каму.",
        "🌊",
        "Набережная Камы",
        85,
        True,
        58.0199,
        56.2476,
        PERM_KAMA,
        ("река", "панорама", "с детьми", "бесплатно"),
    ),
    Place(
        "perm-esplanade-family",
        "Семейная прогулка на эспланаде",
        "parks",
        "Открытые дорожки городской эспланады с местами для отдыха между театральным и мемориальным кварталами.",
        "🌳",
        "Эспланада",
        75,
        True,
        58.0102,
        56.2225,
        PERM_CITY,
        ("прогулка", "семья", "с детьми", "бесплатно"),
    ),
    Place(
        "perm-tatishchev-square",
        "Площадь у памятника Татищеву и де Геннину",
        "sights",
        "Общественное пространство у городского памятника основателям Перми.",
        "🗿",
        "Ленинский район",
        45,
        True,
        58.0118,
        56.2426,
        PERM_HISTORY,
        ("памятник", "история", "архитектура", "с детьми", "бесплатно"),
    ),
    Place(
        "perm-station-garden",
        "Сад имени 250-летия Перми",
        "parks",
        "Зелёная территория рядом с Пермскими воротами и железнодорожным вокзалом.",
        "🌳",
        "Дзержинский район",
        90,
        True,
        58.0044,
        56.1939,
        PERM_CITY,
        ("сад", "парк", "прогулка", "с детьми", "бесплатно"),
    ),
    Place(
        "perm-motovilikha-pond",
        "Мотовилихинский пруд — берег",
        "parks",
        "Общественная прогулочная зона Мотовилихи у промышленного исторического района.",
        "🌊",
        "Мотовилиха",
        100,
        True,
        58.0461,
        56.3066,
        PERM_CITY,
        ("пруд", "история", "прогулка", "с детьми", "бесплатно"),
    ),
    Place(
        "perm-motovilikha-history-square",
        "Площадь промышленной Мотовилихи",
        "sights",
        "Открытая городская среда вокруг мемориального квартала Мотовилихи и исторических заводских улиц.",
        "🏭",
        "Мотовилиха — рабочий посёлок",
        65,
        True,
        58.0385,
        56.312,
        PERM_HISTORY,
        ("индустрия", "история", "с детьми", "бесплатно"),
    ),
    Place(
        "perm-river-perm1-square",
        "Историческое здание вокзала Пермь-1 — фасад",
        "sights",
        "Архитектурный памятник железнодорожной истории у старого вокзала; осмотр только с общественных улиц.",
        "🚉",
        "Пермь-1",
        50,
        True,
        58.0236,
        56.2549,
        PERM_HISTORY,
        ("вокзал", "железная дорога", "история", "с детьми", "бесплатно"),
    ),
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
        ),duration_minutes=305,
        distance_km=2.4,
        place_slugs=(
            "meshkov-house",
            "perm-antiquities-museum",
            "front-and-rear-monument",
            "theatre-theatre",
        ),
    ),
    RoutePlan(
        slug="perm-kama-walk",
        title="Пермь и Кама",
        summary="Исторический центр, музейный квартал и прогулка к Каме.",duration_minutes=295,
        distance_km=3.0,
        place_slugs=("razgulyai-perm", "meshkov-house", "kama-embankment-perm"),
    ),
    RoutePlan(
        slug="perm-motovilikha",
        title="Инженерная Мотовилиха",
        summary="Промышленная история Перми через музей инженера Славянова и музей-диораму на горе Вышка.",
        duration_minutes=240,
        distance_km=2.0,
        place_slugs=("slavyanov-house", "perm-diorama"),
    ),
    RoutePlan(
        slug="perm-art-city",
        title="Искусство и город",
        summary=(
            "Художественная галерея, городские арт-объекты и "
            "центральная эспланада."
        ),duration_minutes=310,
        distance_km=4.0,
        place_slugs=(
            "perm-art-gallery",
            "permyak-salty-ears",
            "front-and-rear-monument",
            "perm-esplanade",
        ),
    ),
    RoutePlan(
        slug="perm-family-science",
        title="Пермь с детьми: наука и открытия",
        summary=(
            "Интерактивный музей, пермская палеонтология и планетарий "
            "в одном семейном маршруте."
        ),
        duration_minutes=330,
        distance_km=2.8,
        place_slugs=(
            "perm-childrens-museum-center",
            "perm-antiquities-museum",
            "perm-planetarium",
        ),
    ),
    RoutePlan(
        slug="perm-stage-and-contemporary-art",
        title="Сцена и современное искусство",
        summary=(
            "Театральная и современная культурная Пермь: от эспланады "
            "и PERMM к исторической оперной сцене."
        ),
        duration_minutes=270,
        distance_km=3.2,
        place_slugs=(
            "theatre-theatre",
            "permm",
            "perm-opera",
        ),
    ),
    RoutePlan(
        "perm-museum-printing",
        "История типографий и железной дороги",
        "Дом-музей подпольщиков и памятники заводского и железнодорожного города; между кварталами нужен транспорт.",
        315,
        8.1,
        ("perm-underground-printshop", "perm-river-perm1-square", "razgulyai-perm"),
    ),
    RoutePlan(
        "perm-gorky-family-park",
        "Парк Горького для семьи",
        "Парк Горького и историческая ротонда в пределах зелёной территории.",
        205,
        2.4,
        ("gorky-park-perm", "perm-gorky-rotunda"),
    ),
    RoutePlan(
        "perm-art-walk",
        "Театральная и художественная Пермь",
        "Театр оперы, Театральный сквер и художественная коллекция.",
        285,
        2.6,
        ("perm-opera", "perm-theatre-square", "perm-art-gallery"),
    ),
    RoutePlan(
        "perm-motovilikha-lake",
        "Мотовилихинская прогулка",
        "Городские исторические кварталы и пруд Мотовилихи.",
        310,
        3,
        ("perm-motovilikha-history-square", "perm-motovilikha-pond", "perm-diorama"),
    ),
    RoutePlan(
        "perm-railway-garden",
        "У железнодорожного вокзала",
        "Открытые аллеи сада имени 250-летия Перми и деревянный арт-объект.",
        205,
        2.4,
        ("perm-gates", "perm-station-garden"),
    ),
    RoutePlan(
        "perm-history-cathedral",
        "Разгуляй и старый город",
        "Исторический квартал, собор и Дом Мешкова с внешним осмотром архитектуры.",
        255,
        3.2,
        ("razgulyai-perm", "perm-peter-paul-cathedral", "perm-meshkov-facade"),
    ),
    RoutePlan(
        "perm-science-family",
        "Музей древностей с детьми",
        "Геологическая история, интерактивный семейный музей и пешеходный отдых у театра.",
        295,
        3.2,
        ("perm-antiquities-museum", "perm-museum-ancient-family", "perm-theatre-square"),
    ),
)

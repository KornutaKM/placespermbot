from datetime import date

from app.domain import Place, PlaceSource, RoutePlan

CITY_SLUG = "kazan"
CITY_NAME = "Казань"
SOURCE_CHECKED_AT = date(2026, 10, 1)

VISIT_TATARSTAN = PlaceSource(
    name="Visit Tatarstan — официальный туристический портал",
    url="https://www.visit-tatarstan.com/places/sightseeings/kazanskiy-kreml/",
    checked_at=SOURCE_CHECKED_AT,
)
BAUMAN_SOURCE = PlaceSource(
    name="Visit Tatarstan — улица Баумана",
    url="https://www.visit-tatarstan.com/places/sightseeings/ulica_baumana/",
    checked_at=SOURCE_CHECKED_AT,
)
KUL_SHARIF_SOURCE = PlaceSource(
    name="Visit Tatarstan — мечеть Кул Шариф",
    url="https://visit-tatarstan.com/places/attractions/kul-sharif/",
    checked_at=SOURCE_CHECKED_AT,
)
CHAK_CHAK_SOURCE = PlaceSource(
    name="Visit Tatarstan — Музей чак-чака",
    url="https://visit-tatarstan.com/places/cultural/muzej_chak-chaka/",
    checked_at=SOURCE_CHECKED_AT,
)
URITSKY_SOURCE = PlaceSource(
    name="Visit Tatarstan — парк Урицкого",
    url="https://visit-tatarstan.com/places/parki-i-mesta-dlya-progulok/park_urickogo/",
    checked_at=SOURCE_CHECKED_AT,
)
EMBANKMENT_SOURCE = PlaceSource(
    name="Visit Tatarstan — Кремлёвская набережная",
    url="https://www.visit-tatarstan.com/en/places/attractions/kremlevskaya_naberezhnaya/",
    checked_at=SOURCE_CHECKED_AT,
)

EDITORIAL_CHECKED_AT = date(2026, 10, 8)

CITY_PORTAL = PlaceSource(
    name="Официальный туристический портал Казани — каталог достопримечательностей",
    url="https://go.kzn.ru/places",
    checked_at=EDITORIAL_CHECKED_AT,
)

KAZAN_MARJANI = PlaceSource(
    name="Туристический портал Казани — Старо-Татарская слобода",
    url="https://go.kzn.ru/places/staro-tatarskaia-sloboda",
    checked_at=EDITORIAL_CHECKED_AT,
)

KAZAN_ISLAM = PlaceSource(
    name="Туристический портал Казани — Музей исламской культуры",
    url="https://go.kzn.ru/places/muzei-islamskoi-kultury",
    checked_at=EDITORIAL_CHECKED_AT,
)

KAZAN_TUKAY = PlaceSource(
    name="Туристический портал Казани — Литературный музей Габдуллы Тукая",
    url="https://go.kzn.ru/places/literaturnyi-muzei-gtukaia",
    checked_at=EDITORIAL_CHECKED_AT,
)

KAZAN_NASYRI = PlaceSource(
    name="Туристический портал Казани — Музей Каюма Насыри",
    url="https://go.kzn.ru/places/muzei-kaiuma-nasyri",
    checked_at=EDITORIAL_CHECKED_AT,
)

KAZAN_LITERATURE = PlaceSource(
    name="Туристический портал Казани — Дом татарской книги",
    url="https://go.kzn.ru/places/muzei-kvartira-skamala",
    checked_at=EDITORIAL_CHECKED_AT,
)

KAZAN_PARK = PlaceSource(
    name="Туристический портал Казани — парк имени Горького",
    url="https://go.kzn.ru/places/park-imgorkogo",
    checked_at=EDITORIAL_CHECKED_AT,
)

KAZAN_WHITES = PlaceSource(
    name="Туристический портал Казани — бульвар «Белые цветы»",
    url="https://go.kzn.ru/places/bulvar-ak-cacaklar-belye-cvety",
    checked_at=EDITORIAL_CHECKED_AT,
)

KAZAN_MEMORIAL = PlaceSource(
    name="Туристический портал Казани — мемориал «Книга Памяти»",
    url="https://go.kzn.ru/places/istoriko-memorialnyi-kompleks-kniga-pamiati",
    checked_at=EDITORIAL_CHECKED_AT,
)

KAZAN_TUGAN = PlaceSource(
    name="Туристический портал Казани — комплекс «Туган Авылым»",
    url="https://go.kzn.ru/places/nacionalnyi-kompleks-tugan-avylym",
    checked_at=EDITORIAL_CHECKED_AT,
)

KAZAN_FAMILY = PlaceSource(
    name="Туристический портал Казани — Центр семьи «Казан»",
    url="https://go.kzn.ru/places/centr-semi-kazan",
    checked_at=EDITORIAL_CHECKED_AT,
)

KAZAN_LITERARY_ROUTE = PlaceSource(
    name="Официальный туристический портал Казани — маршрут татарских писателей",
    url="https://go.kzn.ru/routes/kazan-v-sudbax-tatarskix-pisatelei",
    checked_at=EDITORIAL_CHECKED_AT,
)

KAZAN_GREENS = PlaceSource(
    name="Официальный туристический портал Казани — зелёный маршрут",
    url="https://go.kzn.ru/routes/zelenaia-kazan-parkovoe-ocarovanie",
    checked_at=EDITORIAL_CHECKED_AT,
)

CATEGORY_LABELS = {
    "sights": "🏛 Достопримечательности",
    "unusual": "✨ Необычные места",
    "museums": "🖼 Музеи и культура",
    "parks": "🌿 Парки и прогулки",
    "family": "👨‍👩‍👧 С детьми",
    "free": "💸 Бесплатно",
}

PLACES = (
    Place("kazan-kremlin", "Казанский Кремль", "sights", "Исторический центр Казани, музей-заповедник и объект Всемирного наследия ЮНЕСКО.", "🏰", "Вахитовский район", 120, True, 55.7989, 49.1050, VISIT_TATARSTAN, ("история", "архитектура", "кремль", "центр", "бесплатно")),
    Place("kul-sharif", "Мечеть Кул Шариф", "sights", "Современный архитектурный символ Казани на территории Казанского Кремля.", "🕌", "Вахитовский район", 45, True, 55.7983, 49.1052, KUL_SHARIF_SOURCE, ("архитектура", "религия", "кремль", "центр", "бесплатно")),
    Place("bauman-street", "Улица Баумана", "sights", "Главная пешеходная улица исторического центра с архитектурой, памятниками, кафе и городскими символами.", "🚶", "Вахитовский район", 90, True, 55.7902, 49.1125, BAUMAN_SOURCE, ("прогулка", "архитектура", "центр", "с детьми", "бесплатно")),
    Place("kremlin-embankment-kazan", "Кремлёвская набережная", "parks", "Благоустроенная прогулочная набережная Казанки от Кремля в сторону Национальной библиотеки.", "🌊", "Вахитовский район", 90, True, 55.8009, 49.1177, EMBANKMENT_SOURCE, ("набережная", "прогулка", "виды", "с детьми", "бесплатно")),
    Place("suyumbike-tower", "Башня Сююмбике", "sights", "Один из архитектурных символов Казанского Кремля и узнаваемая историческая вертикаль города.", "🗼", "Вахитовский район", 30, True, 55.8004, 49.1054, VISIT_TATARSTAN, ("история", "архитектура", "кремль", "центр", "бесплатно")),
    Place("family-center-kazan", "Центр семьи «Казан»", "sights", "Современный дворец бракосочетаний в форме чаши и панорамная доминанта у Казанки.", "🏺", "Ново-Савиновский район", 60, True, 55.8124, 49.1080, EMBANKMENT_SOURCE, ("современная архитектура", "виды", "прогулка", "бесплатно")),
    Place("old-tatar-quarter", "Старо-Татарская слобода", "sights", "Исторический район с татарской городской архитектурой, мечетями и прогулочными улицами.", "🏘", "Вахитовский район", 90, True, 55.7815, 49.1155, VISIT_TATARSTAN, ("история", "архитектура", "прогулка", "бесплатно")),
    Place("kaban-embankment", "Набережная озера Кабан", "parks", "Благоустроенная городская набережная для прогулок рядом со Старо-Татарской слободой.", "🌊", "Вахитовский район", 75, True, 55.7829, 49.1210, VISIT_TATARSTAN, ("набережная", "прогулка", "с детьми", "бесплатно")),
    Place("farmers-palace-kazan", "Дворец земледельцев", "sights", "Монументальный современный дворец рядом с Казанским Кремлём и Казанкой.", "🏛", "Вахитовский район", 35, True, 55.8007, 49.1114, VISIT_TATARSTAN, ("архитектура", "центр", "прогулка", "бесплатно")),
    Place("national-museum-tatarstan", "Национальный музей Татарстана", "museums", "Крупный музей истории и культуры Татарстана напротив Казанского Кремля.", "🖼", "Вахитовский район", 120, False, 55.7955, 49.1081, VISIT_TATARSTAN, ("музей", "история", "культура")),
    Place("black-lake-kazan", "Парк «Чёрное озеро»", "parks", "Центральный городской парк для короткой прогулки между Кремлём и университетским кварталом.", "🌳", "Вахитовский район", 60, True, 55.7930, 49.1210, VISIT_TATARSTAN, ("парк", "прогулка", "центр", "бесплатно")),
    Place("chak-chak-museum-kazan", "Музей чак-чака", "museums", "Интерактивный музей в Старо-Татарской слободе о татарском быте, традициях и национальном десерте.", "🍯", "Вахитовский район", 90, False, 55.7811, 49.1165, CHAK_CHAK_SOURCE, ("музей", "татарская культура", "гастрономия", "традиции")),
    Place("uritsky-park-kazan", "Парк Урицкого", "parks", "Большой районный парк с озером, прогулочными дорожками, спортивными зонами и современной детской площадкой.", "🦆", "Московский район", 120, True, 55.8410, 49.0590, URITSKY_SOURCE, ("парк", "с детьми", "прогулка", "спорт", "бесплатно")),
    Place("peter-paul-cathedral-kazan", "Петропавловский собор", "sights", "Исторический православный собор XVIII века в центре Казани.", "⛪", "Вахитовский район", 40, True, 55.7934, 49.1151, VISIT_TATARSTAN, ("архитектура", "история", "религия", "бесплатно")),
    Place(
        "kaz-marjani-mosque",
        "Мечеть аль-Марджани — внешний осмотр",
        "sights",
        "Историческая мечеть XVIII века в Старо-Татарской слободе; соблюдайте порядок действующего храма, внешний осмотр с улицы свободен.",
        "🕌",
        "Старо-Татарская слобода",
        50,
        True,
        55.7795,
        49.1165,
        KAZAN_MARJANI,
        ("мечеть", "Марджани", "татарская история", "архитектура", "бесплатно"),
    ),
    Place(
        "kaz-islamic-culture-museum",
        "Музей исламской культуры",
        "museums",
        "Экспозиция на цокольном этаже мечети Кул-Шариф; вход в музей по отдельному билету.",
        "🖼",
        "Казанский кремль",
        95,
        False,
        55.7982,
        49.1053,
        KAZAN_ISLAM,
        ("музей", "исламская культура", "архитектура", "с детьми"),
    ),
    Place(
        "kaz-tukay-literary-museum",
        "Литературный музей Габдуллы Тукая",
        "museums",
        "Музей поэта в историческом Доме Шамиля на улице Габдуллы Тукая, 74; интерактивные экспозиции.",
        "📚",
        "Улица Тукая",
        105,
        False,
        55.7751,
        49.1169,
        KAZAN_TUKAY,
        ("музей", "Тукай", "литература", "с детьми"),
    ),
    Place(
        "kaz-kayum-nasyri-museum",
        "Музей Каюма Насыри",
        "museums",
        "Мемориальная экспозиция татарского просветителя на улице Парижской Коммуны, 35.",
        "📚",
        "Улица Парижской Коммуны",
        95,
        False,
        55.7822,
        49.1176,
        KAZAN_NASYRI,
        ("музей", "Насыри", "наука", "с детьми"),
    ),
    Place(
        "kaz-tatar-merchants-museum",
        "Музей татарского купечества",
        "museums",
        "Культурная экспозиция на улице Каюма Насыри, 11 об истории татарских купеческих династий.",
        "🏺",
        "Улица Каюма Насыри",
        100,
        False,
        55.7808,
        49.1187,
        CITY_PORTAL,
        ("музей", "купцы", "татарская культура", "с детьми"),
    ),
    Place(
        "kaz-sharif-kamal-literature",
        "Музей истории татарской литературы — квартира Шарифа Камала",
        "museums",
        "Музейная площадка «Дом татарской книги» об истории татарской литературы; экскурсии и мероприятия по программе.",
        "📖",
        "Литературная Казань",
        95,
        False,
        55.7849,
        49.1138,
        KAZAN_LITERATURE,
        ("музей", "Шариф Камал", "литература", "с детьми"),
    ),
    Place(
        "kaz-book-of-memory",
        "Историко-мемориальный комплекс «Книга Памяти»",
        "museums",
        "Музейно-мемориальное пространство в Парке Победы с материалами о людях и событиях войны.",
        "🎖",
        "Парк Победы",
        90,
        False,
        55.8301,
        49.1153,
        KAZAN_MEMORIAL,
        ("музей", "история", "война", "с детьми"),
    ),
    Place(
        "kaz-gorky-central-park",
        "Центральный парк имени Горького",
        "parks",
        "Большой парк с прогулочными аллеями, детскими площадками и сезонным фонтаном; отдельные развлечения платные.",
        "🌳",
        "Парк Горького",
        100,
        True,
        55.8008,
        49.1482,
        KAZAN_PARK,
        ("парк", "аллеи", "прогулка", "с детьми", "бесплатно"),
    ),
    Place(
        "kaz-victory-park",
        "Парк Победы",
        "parks",
        "Открытая парковая территория с мемориальными объектами и аллеями у проспекта Ямашева.",
        "🌲",
        "Парк Победы",
        95,
        True,
        55.8306,
        49.1149,
        KAZAN_MEMORIAL,
        ("парк", "история", "прогулка", "с детьми", "бесплатно"),
    ),
    Place(
        "kaz-white-flowers-boulevard",
        "Бульвар «Белые цветы»",
        "parks",
        "Благоустроенный пешеходный бульвар в Ново-Савиновском районе, связывающий парк и жилые кварталы.",
        "🌼",
        "Бульвар Ак Чәчәкләр",
        90,
        True,
        55.8255,
        49.115,
        KAZAN_WHITES,
        ("бульвар", "прогулка", "с детьми", "бесплатно"),
    ),
    Place(
        "kaz-tugan-avylym",
        "Национальный комплекс «Туган Авылым»",
        "family",
        "Семейное пространство с татарскими ремёслами и гастрономией на улице Туфана Миннуллина, 14/56; мастер-классы и развлечения оплачиваются отдельно.",
        "🏘",
        "Суконная слобода",
        105,
        True,
        55.777,
        49.1372,
        KAZAN_TUGAN,
        ("семья", "татарские традиции", "ремёсла", "с детьми", "бесплатно"),
    ),
    Place(
        "kaz-family-center-observation",
        "Смотровая площадка Центра семьи «Казан»",
        "unusual",
        "Платный обзорный уровень здания в форме казана; подъём допускается по текущему расписанию.",
        "🔭",
        "Ново-Савиновская набережная",
        75,
        False,
        55.8124,
        49.1081,
        KAZAN_FAMILY,
        ("смотровая площадка", "панорама", "с детьми"),
    ),
    Place(
        "kaz-kamal-theatre-exterior",
        "Татарский театр имени Галиасгара Камала — фасад",
        "sights",
        "Городской архитектурный объект рядом с озером Кабан; спектакли и закрытые помещения доступны отдельно.",
        "🎭",
        "Озеро Кабан",
        40,
        True,
        55.7761,
        49.1245,
        KAZAN_MARJANI,
        ("театр", "татарская культура", "архитектура", "бесплатно"),
    ),
    Place(
        "kaz-musa-jalil-monument",
        "Памятник Мусе Джалилю",
        "sights",
        "Монумент поэту и участнику антифашистского подполья у Казанского кремля; открытая городская площадь.",
        "🗿",
        "Площадь Первого Мая",
        40,
        True,
        55.7961,
        49.1057,
        KAZAN_LITERARY_ROUTE,
        ("Джалиль", "памятник", "литература", "с детьми", "бесплатно"),
    ),
    Place(
        "kaz-zilant-garden",
        "Сквер Зилант",
        "parks",
        "Небольшой городской сквер на улице Миславского, 1/7, рядом с историческим кремлёвским районом.",
        "🌿",
        "Улица Миславского",
        55,
        True,
        55.7957,
        49.1071,
        CITY_PORTAL,
        ("сквер", "центр", "прогулка", "с детьми", "бесплатно"),
    ),
)

ROUTES = (
    RoutePlan("kazan-first-walk", "Первое знакомство с Казанью", "Кремль, Кул Шариф и главная пешеходная улица города.", 240, 2.2, ("kazan-kremlin", "kul-sharif", "suyumbike-tower", "bauman-street")),
    RoutePlan("kazan-kremlin-and-river", "Кремль и Казанка", "Исторический ансамбль Кремля с продолжением прогулки по набережной.", 210, 2.0, ("kazan-kremlin", "kul-sharif", "kremlin-embankment-kazan")),
    RoutePlan("kazan-tatar-quarter", "Татарская Казань", "Старо-Татарская слобода, озеро Кабан и центральные городские пространства.", 240, 3.2, ("old-tatar-quarter", "kaban-embankment", "bauman-street")),
    RoutePlan("kazan-museum-center", "История в центре", "Кремль, Национальный музей и архитектурные достопримечательности рядом.", 300, 2.0, ("kazan-kremlin", "national-museum-tatarstan", "peter-paul-cathedral-kazan", "black-lake-kazan")),
    RoutePlan("kazan-tatar-taste", "Татарская культура и вкус", "Старо-Татарская слобода, музей традиционного десерта и прогулка у озера Кабан.", 270, 2.0, ("old-tatar-quarter", "chak-chak-museum-kazan", "kaban-embankment")),
    RoutePlan("kazan-family-north", "Семейная Казань вне центра", "Спокойный районный сценарий с озером, детской площадкой и прогулочными дорожками парка Урицкого.", 150, 2.0, ("uritsky-park-kazan", "kaz-victory-park", "kaz-white-flowers-boulevard")),
    RoutePlan(
        "kaz-museum-heritage",
        "Музеи Казанского кремля",
        "История Татарстана и отдельная экспозиция исламской культуры; платные музейные залы.",
        315,
        2.1,
        ("kazan-kremlin", "national-museum-tatarstan", "kaz-islamic-culture-museum", "kul-sharif"),
    ),
    RoutePlan(
        "kaz-literary-heritage",
        "Казань татарских писателей",
        "Литературные музеи и памятники в Старо-Татарской слободе; большая часть маршрута пешком.",
        335,
        3.6,
        ("kaz-sharif-kamal-literature", "kaz-kayum-nasyri-museum", "kaz-tukay-literary-museum", "old-tatar-quarter"),
    ),
    RoutePlan(
        "kaz-victory-family",
        "Парк Победы всей семьёй",
        "Семейная прогулка по парку, мемориальному музею и бульвару Белых цветов.",
        280,
        3,
        ("kaz-victory-park", "kaz-book-of-memory", "kaz-white-flowers-boulevard"),
    ),
    RoutePlan(
        "kaz-tatar-houses",
        "История татарского купечества",
        "Купеческие усадьбы, мечеть аль-Марджани и татарские культурные экспозиции.",
        275,
        2.3,
        ("old-tatar-quarter", "kaz-tatar-merchants-museum", "kaz-marjani-mosque", "kaz-kayum-nasyri-museum"),
    ),
    RoutePlan(
        "kaz-park-central",
        "Зелёная Казань",
        "Парк имени Горького и улицы городского центра; маршрут подходит для семейной прогулки.",
        260,
        4.4,
        ("kaz-gorky-central-park", "black-lake-kazan", "kaz-zilant-garden"),
    ),
)

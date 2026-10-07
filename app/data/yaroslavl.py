from datetime import date

from app.city_manifest import CatalogQualityProfile, CityDefinition
from app.domain import Place, PlaceSource, RoutePlan

CITY_SLUG = "yaroslavl"
CITY_NAME = "Ярославль"
SOURCE_CHECKED_AT = date(2026, 10, 1)

YAROSLAVIA = PlaceSource("Ярославия — официальный туристический портал Ярославской области", "https://visityaroslavia.ru/", SOURCE_CHECKED_AT)
YAR_KREMLIN = PlaceSource("Ярославский музей-заповедник", "https://yarkremlin.ru/", SOURCE_CHECKED_AT)
MILITARY_GLORY_SOURCE = PlaceSource(
    "Ярославский музей-заповедник — Музей боевой славы",
    "https://yarkremlin.ru/museum/muzey-boevoy-slavy/",
    SOURCE_CHECKED_AT,
)
CITY_HISTORY_SOURCE = PlaceSource(
    "Музей истории города Ярославля",
    "https://www.mukmig.yaroslavl.ru/",
    SOURCE_CHECKED_AT,
)

CATEGORY_LABELS = {
    "sights": "🏛 Достопримечательности",
    "unusual": "✨ Необычные места",
    "museums": "🖼 Музеи",
    "parks": "🌳 Парки и прогулки",
    "family": "👨‍👩‍👧 С детьми",
    "free": "💸 Бесплатно",
}

PLACES = (
    Place("yaroslavl-museum-reserve", "Ярославский музей-заповедник", "museums", "Историко-архитектурный музейный комплекс в центре Ярославля.", "🏛", "Кировский район", 150, False, 57.6217, 39.8890, YAR_KREMLIN, ("музей", "история", "архитектура")),
    Place("transfiguration-cathedral-yar", "Спасо-Преображенский собор", "sights", "Собор исторического монастырского ансамбля Ярославского музея-заповедника.", "⛪", "Кировский район", 45, False, 57.6215, 39.8895, YAR_KREMLIN, ("история", "архитектура", "религия")),
    Place("volga-embankment-yar", "Волжская набережная", "parks", "Прогулочная набережная исторического центра вдоль Волги.", "🌊", "Кировский район", 90, True, 57.6300, 39.9040, YAROSLAVIA, ("набережная", "прогулка", "виды", "бесплатно")),
    Place("strelka-yar", "Стрелка", "parks", "Парк и панорамная точка у слияния Волги и Которосли.", "🌳", "Кировский район", 75, True, 57.6175, 39.9027, YAROSLAVIA, ("парк", "виды", "прогулка", "бесплатно")),
    Place("elijah-prophet-yar", "Церковь Ильи Пророка", "sights", "Храм XVII века на Советской площади в историческом центре.", "⛪", "Кировский район", 45, False, 57.6265, 39.8945, YAROSLAVIA, ("архитектура", "история", "религия")),
    Place("assumption-cathedral-yar", "Успенский собор", "sights", "Собор на высоком берегу Волги рядом со Стрелкой.", "⛪", "Кировский район", 40, True, 57.6198, 39.9022, YAROSLAVIA, ("архитектура", "религия", "бесплатно")),
    Place("governors-house-yar", "Губернаторский дом", "museums", "Историческая усадьба и художественное музейное пространство на Волжской набережной.", "🖼", "Кировский район", 90, False, 57.6292, 39.8980, YAROSLAVIA, ("музей", "искусство", "усадьба")),
    Place("bear-monument-yar", "Памятник медведю", "unusual", "Городской символ рядом с историческим центром Ярославля.", "🐻", "Кировский район", 20, True, 57.6227, 39.8918, YAROSLAVIA, ("городской символ", "необычное", "бесплатно")),
    Place("damansky-island-yar", "Даманский остров", "parks", "Зелёная прогулочная территория у Которосли рядом со Стрелкой.", "🎡", "Кировский район", 90, True, 57.6157, 39.8978, YAROSLAVIA, ("парк", "с детьми", "прогулка", "бесплатно")),
    Place("sobinov-house-yar", "Дом-музей Л. В. Собинова", "museums", "Мемориальный музей оперного певца Леонида Собинова.", "🎼", "Кировский район", 75, False, 57.6269, 39.8789, YAR_KREMLIN, ("музей", "музыка", "история")),
    Place("epiphany-church-yar", "Церковь Богоявления", "sights", "Яркий храм конца XVII века рядом с Богоявленской площадью.", "⛪", "Кировский район", 35, True, 57.6211, 39.8848, YAROSLAVIA, ("архитектура", "история", "бесплатно")),
    Place("military-glory-yar", "Музей боевой славы", "museums", "Филиал музея-заповедника об истории Ярославля и ярославцев в годы Великой Отечественной войны.", "🎖", "Ленинский район", 90, False, 57.6332, 39.8318, MILITARY_GLORY_SOURCE, ("музей", "военная история", "история", "с детьми")),
    Place("city-history-yar", "Музей истории города Ярославля", "museums", "Городской музей в купеческой усадьбе на Волжской набережной с экспозицией от основания Ярославля до XXI века.", "🏙", "Кировский район", 120, False, 57.6270, 39.8986, CITY_HISTORY_SOURCE, ("музей", "история", "краеведение", "с детьми")),
    Place("kirova-street-yar", "Улица Кирова", "sights", "Пешеходная улица исторического центра с городской архитектурой и кафе.", "🚶", "Кировский район", 60, True, 57.6259, 39.8880, YAROSLAVIA, ("прогулка", "центр", "архитектура", "бесплатно")),
)

ROUTES = (
    RoutePlan("yar-first-walk", "Ярославль впервые", "Главные точки исторического центра от музея-заповедника до Стрелки.", 300, 3.0, ("yaroslavl-museum-reserve", "elijah-prophet-yar", "assumption-cathedral-yar", "strelka-yar")),
    RoutePlan("yar-volga", "Вдоль Волги", "Набережная, художественный музей и панорамы Стрелки.", 240, 2.8, ("governors-house-yar", "volga-embankment-yar", "strelka-yar")),
    RoutePlan("yar-museums", "Музейный Ярославль", "История города, музыка и художественные коллекции.", 360, 3.5, ("yaroslavl-museum-reserve", "sobinov-house-yar", "governors-house-yar")),
    RoutePlan("yar-family", "Семейная прогулка", "Городской символ, пешеходный центр и зелёный Даманский остров.", 210, 2.5, ("bear-monument-yar", "kirova-street-yar", "damansky-island-yar")),
    RoutePlan("yar-history-depth", "Ярославль: история глубже", "Два разных слоя городской истории — военная память и развитие Ярославля от основания до современности.", 300, 6.5, ("military-glory-yar", "city-history-yar", "volga-embankment-yar")),
)


CITY = CityDefinition(
    slug=CITY_SLUG,
    name=CITY_NAME,
    category_labels=CATEGORY_LABELS,
    places=PLACES,
    routes=ROUTES,
    quality=CatalogQualityProfile(
        min_places=14,
        min_routes=5,
        min_districts=2,
        min_categories=3,
        min_free_places=7,
        min_family_places=3,
        min_museums=4,
    ),
)

from datetime import date

from app.city_manifest import CatalogQualityProfile
from app.domain import Place, PlaceSource, RoutePlan

CITY_SLUG = "novosibirsk"
CITY_NAME = "Новосибирск"
SOURCE_CHECKED_AT = date(2026, 10, 1)

WELCOME_NSK = PlaceSource(
    name="Официальный туристический портал Новосибирска",
    url="https://welcome-novosibirsk.ru/place-to-visit/sights/",
    checked_at=SOURCE_CHECKED_AT,
)
WELCOME_NSK_MUSEUMS = PlaceSource(
    name="Официальный туристический портал Новосибирска — музеи и галереи",
    url="https://welcome-novosibirsk.ru/place-to-visit/museums/",
    checked_at=SOURCE_CHECKED_AT,
)
WELCOME_NSK_SIGHTS = PlaceSource(
    name="Официальный туристический портал Новосибирска — достопримечательности",
    url="https://welcome-novosibirsk.ru/place-to-visit/sights/",
    checked_at=SOURCE_CHECKED_AT,
)
CITY_NSK = PlaceSource(
    name="Официальный сайт Новосибирска — достопримечательности",
    url="https://www.novo-sibirsk.ru/about/for-visitors/attractions/",
    checked_at=SOURCE_CHECKED_AT,
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
    Place("novat", "НОВАТ", "sights", "Новосибирский театр оперы и балета — одна из главных архитектурных и культурных доминант города.", "🎭", "Центральный район", 60, True, 55.0302, 82.9247, CITY_NSK, ("театр", "архитектура", "культура", "центр", "бесплатно")),
    Place("lenin-square-nsk", "Площадь Ленина", "sights", "Центральная площадь Новосибирска у НОВАТа и Красного проспекта.", "🏙", "Центральный район", 30, True, 55.0298, 82.9208, WELCOME_NSK, ("центр", "прогулка", "архитектура", "бесплатно")),
    Place("local-history-museum-nsk", "Краеведческий музей", "museums", "Главный краеведческий музей города в историческом Городском торговом корпусе.", "🏛", "Центральный район", 90, False, 55.0294, 82.9203, CITY_NSK, ("музей", "история", "архитектура", "центр")),
    Place("alexander-nevsky-nsk", "Собор Александра Невского", "sights", "Один из старейших каменных храмов Новосибирска на Красном проспекте.", "⛪", "Центральный район", 40, True, 55.0182, 82.9237, CITY_NSK, ("архитектура", "история", "религия", "бесплатно")),
    Place("nikolai-chapel-nsk", "Часовня Николая Чудотворца", "sights", "Небольшая часовня и узнаваемый городской ориентир на Красном проспекте.", "⛪", "Центральный район", 20, True, 55.0257, 82.9212, CITY_NSK, ("архитектура", "центр", "бесплатно")),
    Place("mikhailovskaya-embankment", "Михайловская набережная", "parks", "Благоустроенная набережная Оби для прогулок и отдыха у реки.", "🌊", "Октябрьский район", 90, True, 55.0066, 82.9388, WELCOME_NSK, ("набережная", "прогулка", "с детьми", "бесплатно")),
    Place("novosibirsk-zoo", "Новосибирский зоопарк", "family", "Крупный зоологический парк имени Ростислава Шило и одно из самых известных семейных мест города.", "🦁", "Заельцовский район", 240, False, 55.0567, 82.8957, CITY_NSK, ("зоопарк", "с детьми", "животные")),
    Place("novosibirsk-main-station", "Новосибирск-Главный", "sights", "Монументальное здание главного железнодорожного вокзала города.", "🚉", "Железнодорожный район", 30, True, 55.0353, 82.8964, CITY_NSK, ("архитектура", "железная дорога", "бесплатно")),
    Place("central-park-nsk", "Центральный парк", "parks", "Один из старейших городских парков Новосибирска рядом с центральными кварталами.", "🌳", "Центральный район", 75, True, 55.0371, 82.9285, WELCOME_NSK, ("парк", "прогулка", "с детьми", "бесплатно")),
    Place("railway-museum-nsk", "Музей железнодорожной техники", "museums", "Открытая коллекция локомотивов, вагонов и железнодорожной техники Западной Сибири.", "🚂", "Советский район", 120, False, 54.9389, 83.0018, WELCOME_NSK, ("музей", "техника", "железная дорога", "с детьми")),
    Place("glory-monument-nsk", "Монумент Славы", "sights", "Мемориальный ансамбль в левобережной части Новосибирска.", "🕯", "Ленинский район", 45, True, 54.9816, 82.8945, CITY_NSK, ("история", "мемориал", "бесплатно")),
    Place("art-museum-nsk", "Новосибирский художественный музей", "museums", "Художественный музей в историческом центре с коллекциями русского и зарубежного искусства.", "🖼", "Центральный район", 120, False, 55.0188, 82.9224, WELCOME_NSK_MUSEUMS, ("музей", "искусство", "культура")),
    Place("museum-embankment-nsk", "Музей на Набережной", "museums", "Филиал Музея Новосибирска рядом с Обью, посвящённый истории города и прибрежных районов.", "🏙", "Октябрьский район", 75, False, 55.0082, 82.9365, WELCOME_NSK_MUSEUMS, ("музей", "история города", "набережная", "с детьми")),
    Place("akademgorodok-nsk", "Академгородок", "unusual", "Научный район Новосибирска с институтами, сосновыми кварталами и особой городской средой.", "🔬", "Советский район", 150, True, 54.8430, 83.0930, WELCOME_NSK, ("наука", "прогулка", "архитектура", "бесплатно"))
)

ROUTES = (
    RoutePlan("nsk-first-walk", "Новосибирск впервые", "Красный проспект от собора через центр к НОВАТу.", 240, 3.0, ("alexander-nevsky-nsk", "nikolai-chapel-nsk", "local-history-museum-nsk", "lenin-square-nsk", "novat")),
    RoutePlan("nsk-river", "Город и Обь", "Центральная прогулка с выходом к Михайловской набережной.", 180, 3.5, ("lenin-square-nsk", "alexander-nevsky-nsk", "mikhailovskaya-embankment")),
    RoutePlan("nsk-family", "Семейный Новосибирск", "Большой семейный день в зоопарке с коротким знакомством с железнодорожной архитектурой города.", 330, 5.0, ("novosibirsk-main-station", "novosibirsk-zoo")),
    RoutePlan("nsk-science", "Научный Новосибирск", "Академгородок и техническая история железной дороги.", 360, 8.0, ("akademgorodok-nsk", "railway-museum-nsk")),
    RoutePlan("nsk-parks-center", "Зелёный центр", "Площадь Ленина, НОВАТ и спокойная прогулка по Центральному парку.", 180, 2.0, ("lenin-square-nsk", "novat", "central-park-nsk")),
    RoutePlan("nsk-art-river", "Искусство и Обь", "Художественная коллекция центра, история города у реки и прогулка по Михайловской набережной.", 300, 3.5, ("art-museum-nsk", "museum-embankment-nsk", "mikhailovskaya-embankment")),
)


QUALITY_PROFILE = CatalogQualityProfile(
    min_places=14,
    min_routes=6,
    min_districts=6,
    min_categories=4,
    min_free_places=7,
    min_family_places=4,
    min_museums=4,
)

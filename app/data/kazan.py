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
EMBANKMENT_SOURCE = PlaceSource(
    name="Visit Tatarstan — Кремлёвская набережная",
    url="https://www.visit-tatarstan.com/en/places/attractions/kremlevskaya_naberezhnaya/",
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
    Place("kazan-kremlin", "Казанский Кремль", "sights", "Исторический центр Казани, музей-заповедник и объект Всемирного наследия ЮНЕСКО.", "🏰", "Вахитовский район", 120, True, 55.7989, 49.1050, VISIT_TATARSTAN, ("история", "архитектура", "кремль", "центр", "бесплатно")),
    Place("kul-sharif", "Мечеть Кул Шариф", "sights", "Современный архитектурный символ Казани на территории Казанского Кремля.", "🕌", "Вахитовский район", 45, True, 55.7983, 49.1052, KUL_SHARIF_SOURCE, ("архитектура", "религия", "кремль", "центр", "бесплатно")),
    Place("bauman-street", "Улица Баумана", "sights", "Главная пешеходная улица исторического центра с архитектурой, памятниками, кафе и городскими символами.", "🚶", "Вахитовский район", 90, True, 55.7902, 49.1125, BAUMAN_SOURCE, ("прогулка", "архитектура", "центр", "с детьми", "бесплатно")),
    Place("kremlin-embankment-kazan", "Кремлёвская набережная", "parks", "Благоустроенная прогулочная набережная Казанки от Кремля в сторону Национальной библиотеки.", "🌊", "Вахитовский район", 90, True, 55.8009, 49.1177, EMBANKMENT_SOURCE, ("набережная", "прогулка", "виды", "с детьми", "бесплатно")),
    Place("suyumbike-tower", "Башня Сююмбике", "sights", "Один из архитектурных символов Казанского Кремля и узнаваемая историческая вертикаль города.", "🗼", "Вахитовский район", 30, True, 55.8004, 49.1054, VISIT_TATARSTAN, ("история", "архитектура", "кремль", "центр", "бесплатно")),
)

ROUTES = (
    RoutePlan("kazan-first-walk", "Первое знакомство с Казанью", "Кремль, Кул Шариф и главная пешеходная улица города.", 240, 2.2, ("kazan-kremlin", "kul-sharif", "suyumbike-tower", "bauman-street")),
    RoutePlan("kazan-kremlin-and-river", "Кремль и Казанка", "Исторический ансамбль Кремля с продолжением прогулки по набережной.", 210, 2.0, ("kazan-kremlin", "kul-sharif", "kremlin-embankment-kazan")),
)

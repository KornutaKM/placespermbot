from datetime import date

from app.domain import Place, PlaceSource, RoutePlan

CITY_SLUG = "yekaterinburg"
CITY_NAME = "Екатеринбург"
SOURCE_CHECKED_AT = date(2026, 10, 1)

CITY_CENTER_SOURCE = PlaceSource(
    name="Маршрут по историческому центру Екатеринбурга",
    url="https://achotut.ru/pervouralsk/marshruty/tsentr-yekaterinburga-ot-plotinki-do-khrama-na-krovi",
    checked_at=SOURCE_CHECKED_AT,
)
CHURCH_SOURCE = PlaceSource(
    name="Екатеринбургская епархия — Храм на Крови",
    url="https://ekaterinburg-eparhia.ru/building/chrames/11/",
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
    Place("plotinka", "Плотинка и Исторический сквер", "sights", "Историческое ядро Екатеринбурга на месте плотины городского пруда и старого завода.", "🌊", "Ленинский район", 60, True, 56.8375, 60.6057, CITY_CENTER_SOURCE, ("история", "прогулка", "центр", "с детьми", "бесплатно")),
    Place("sevastyanov-house", "Дом Севастьянова", "sights", "Яркий исторический особняк на проспекте Ленина у городского пруда.", "🏛", "Кировский район", 25, True, 56.8396, 60.6080, CITY_CENTER_SOURCE, ("архитектура", "история", "центр", "бесплатно")),
    Place("church-on-blood", "Храм на Крови", "sights", "Храм-памятник на месте дома Ипатьева, завершённый и освящённый в 2003 году.", "⛪", "Кировский район", 45, True, 56.8444, 60.6086, CHURCH_SOURCE, ("история", "архитектура", "религия", "центр", "бесплатно")),
    Place("yeltsin-center", "Ельцин Центр", "museums", "Музейный и общественный комплекс, посвящённый российской истории конца XX века.", "🖼", "Верх-Исетский район", 180, False, 56.8447, 60.5914, CITY_CENTER_SOURCE, ("музей", "история", "современность")),
    Place("literary-quarter", "Литературный квартал", "museums", "Исторический квартал с литературными музеями и городской деревянной архитектурой.", "📚", "Кировский район", 90, False, 56.8448, 60.6117, CITY_CENTER_SOURCE, ("музей", "литература", "история", "архитектура")),
    Place("kharitonovsky-garden", "Харитоновский сад", "parks", "Исторический городской сад рядом с усадьбой Расторгуевых — Харитоновых.", "🌳", "Кировский район", 60, True, 56.8462, 60.6126, CITY_CENTER_SOURCE, ("парк", "прогулка", "история", "бесплатно")),
    Place("weiner-street", "Улица Вайнера", "sights", "Центральная пешеходная улица Екатеринбурга с городской скульптурой и торговой историей.", "🚶", "Ленинский район", 60, True, 56.8320, 60.5986, CITY_CENTER_SOURCE, ("прогулка", "центр", "городское искусство", "бесплатно")),
    Place("square-1905", "Площадь 1905 года", "sights", "Главная городская площадь Екатеринбурга и важная точка центрального пешеходного маршрута.", "🏙", "Ленинский район", 30, True, 56.8370, 60.5965, CITY_CENTER_SOURCE, ("история", "центр", "архитектура", "бесплатно")),
)

ROUTES = (
    RoutePlan("ekb-first-walk", "Екатеринбург впервые", "Пешеходное знакомство с историческим ядром от площади 1905 года до Храма на Крови.", 270, 3.4, ("square-1905", "weiner-street", "plotinka", "sevastyanov-house", "church-on-blood")),
    RoutePlan("ekb-history", "История Екатеринбурга", "Исторический сквер, литературный квартал и ключевые места истории XX века.", 360, 4.0, ("plotinka", "literary-quarter", "church-on-blood", "yeltsin-center")),
    RoutePlan("ekb-green-center", "Зелёный центр", "Короткая прогулка через исторический центр к Харитоновскому саду.", 150, 2.1, ("plotinka", "sevastyanov-house", "kharitonovsky-garden")),
)

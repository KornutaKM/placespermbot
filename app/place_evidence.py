"""Point-specific documentary evidence, separate from catalog/source timestamps.

An operator listing does not certify that a venue is open at the moment of a
visit. Unlisted places stay UNKNOWN; no OSM or HTTP result grants verification.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from html import escape
from urllib.parse import urlparse

from app.catalog import CityCatalog, list_catalogs


@dataclass(frozen=True, slots=True)
class Evidence:
    city_slug: str
    place_slug: str
    status: str
    checked_on: date
    evidence_url: str
    finding: str


EVIDENCE = (
    Evidence("perm", "meshkov-house", "operator_listed", date(2026, 10, 11),
             "https://museumperm.ru/visit",
             "Музей перечислен на официальной странице с адресом и режимом приёма."),
    Evidence("perm", "perm-meshkov-facade", "operator_listed", date(2026, 10, 11),
             "https://museumperm.ru/branches",
             "Существование Дома Мешкова подтверждено сайтом музея."),
    Evidence("perm", "perm-antiquities-museum", "operator_listed", date(2026, 10, 11),
             "https://museumperm.ru/branch/mpd",
             "Музей на Сибирской, 15 перечислен на сайте оператора."),
    Evidence("perm", "perm-museum-ancient-family", "operator_listed",
             date(2026, 10, 11), "https://museumperm.ru/branch/mpd",
             "Экспозиция на 4 этаже; для МГН доступ ограничен."),
    Evidence("perm", "perm-childrens-museum-center", "operator_listed",
             date(2026, 10, 11), "https://museumperm.ru/branch/kids",
             "С 15 апреля 2026 года центр работает на Советской, 1."),
    Evidence("perm", "perm-diorama", "operator_listed", date(2026, 10, 11),
             "https://museumperm.ru/visit",
             "Официальная страница указывает Огородникова, 2 и дни посещения."),
    Evidence("perm", "slavyanov-house", "operator_listed", date(2026, 10, 11),
             "https://museumperm.ru/visit",
             "Официальная страница указывает музей на ул. 1905 года, 37."),
    Evidence("perm", "perm-underground-printshop", "operator_listed",
             date(2026, 10, 11), "https://museumperm.ru/branch/podpolka",
             "Дом-музей на Монастырской, 142: сезонный режим работы."),
    Evidence("perm", "gorky-park-perm", "operator_listed", date(2026, 10, 11),
             "https://www.parkperm.ru/",
             "Оператор публикует режим работы парка и октябрьские акции 2026."),
    Evidence("perm", "theatre-theatre", "operator_listed", date(2026, 10, 11),
             "https://teatr-teatr.com/",
             "Официальный сайт публикует спектакли октября 2026."),
    Evidence("perm", "perm-opera", "operator_listed", date(2026, 10, 11),
             "https://permopera.ru/playbills/playbill/",
             "Официальная афиша содержит спектакли октября 2026."),
    Evidence("perm", "perm-art-gallery", "operator_listed", date(2026, 10, 11),
             "https://tickets.permartmuseum.ru/place/2",
             "Официальная продажа билетов по адресу Советская, 1, корпус 5."),
    Evidence("perm", "permm", "operator_listed", date(2026, 10, 11),
             "https://permm.ru/~/afisha",
             "Официальная афиша указывает Крисанова, 4 и режим музея."),
    Evidence("perm", "perm-zoo", "operator_listed", date(2026, 10, 11),
             "https://zoo.perm.ru/news/2026/09/30/2115",
             "Официальное сообщение от 30 сентября 2026 года о зимнем режиме."),
    Evidence(
        "volgograd", "alexander-nevsky-cathedral-vlg", "operator_listed",
        date(2026, 10, 11),
        "https://alexan-nevsk-sob.cerkov.ru/",
        "Официальная приходская страница кафедрального собора указывает "
        "статус «действующий» и адрес Александровский сад. "
        "Доступ в конкретный день и ограничения уточняйте у прихода.",
    ),
    Evidence(
        "murmansk", "murmansk-icebreaker-lenin", "operator_listed",
        date(2026, 10, 11),
        "https://www.rosatomflot.ru/atomnyy-ledokol-lenin/grafik-raboty/",
        "Росатомфлот описывает экскурсионные сеансы и порядок покупки именных "
        "электронных билетов. Наличие мест и допуск на конкретную дату "
        "нужно уточнять у оператора.",
    ),
    Evidence(
        "murmansk", "murmansk-crafts-house", "operator_listed",
        date(2026, 10, 11),
        "https://www.artmmuseum.ru/history/",
        "Мурманский областной художественный музей перечисляет Дом ремёсел "
        "как свой отдел на улице Книповича, 23А. Актуальное расписание "
        "занятий и выставок уточняйте у музея.",
    ),
    Evidence(
        "sochi", "winter-theatre-sochi", "operator_listed",
        date(2026, 10, 11),
        "https://www.skfo.online/contacts/",
        "Муниципальный оператор Зимнего театра указывает Театральную, 2 "
        "и кассы. Спектакли, билеты и внутренний доступ уточняйте "
        "по актуальной афише учреждения.",
    ),
    Evidence(
        "sochi", "marine-station-sochi", "operator_listed",
        date(2026, 10, 11),
        "https://www.morport-sochi.ru/contacts/",
        "АО «Морпорт Сочи» указывает фактический адрес Войкова, 1. "
        "Это операторское свидетельство об объекте порта, но не "
        "подтверждение свободного доступа в историческое здание "
        "или на причалы.",
    ),
    Evidence(
        "kursk", "kursk-deineka", "operator_listed",
        date(2026, 10, 11),
        "https://deinekagallery.ru/posetitelyam/",
        "Оператор указывает действующий выставочный зал на Радищева, 85 "
        "(в отличие от административного здания на Советской, 3). "
        "Доступность конкретной выставки и часы уточняйте перед поездкой.",
    ),
    Evidence(
        "kursk", "kursk-znamensky", "operator_listed",
        date(2026, 10, 11),
        "https://kursk-znamen-1.cerkov.ru/",
        "Официальный сайт действующего Знаменского монастыря указывает "
        "Луначарского, 4 и богослужения. Доступ к собору и правила "
        "посещения уточняйте в монастыре.",
    ),
    Evidence(
        "kursk", "kursk-sergiev", "operator_listed",
        date(2026, 10, 11),
        "https://serge-kazan.cerkov.ru/",
        "Официальный сайт Сергиево-Казанского собора описывает храм "
        "и общее расписание служб. Реальный доступ в конкретный день "
        "уточняйте в приходе.",
    ),
    Evidence(
        "kursk", "kursk-pushkin", "operator_listed",
        date(2026, 10, 11),
        "https://kurskdrama.ru/kontakty/",
        "Официальный драмтеатр указывает Ленина, 26 и расписание кассы; "
        "в афише на октябрь 2026 есть постановки. Осмотр фасада снаружи "
        "не подтверждает свободного доступа в зал; билеты и правила уточняйте.",
    ),
    Evidence(
        "syktyvkar", "syktyvkar-national-museum", "operator_listed",
        date(2026, 10, 11),
        "https://museumkomi.ru/?page_id=1609",
        "Сайт Национального музея подтверждает отдел природы и выставочный "
        "зал на Коммунистической, 6 и режим. Отдел истории на Ленина, 57 "
        "объявлен закрытым на ремонт; вход в конкретный день уточняйте.",
    ),
    Evidence(
        "syktyvkar", "syktyvkar-national-gallery", "operator_listed",
        date(2026, 10, 11),
        "https://ngrkomi-art.ru/",
        "Официальный сайт Национальной галереи указывает Кирова, 44 "
        "и октябрьские выставки 2026 года. Наличие билетов и вход "
        "в конкретный день необходимо уточнять.",
    ),
    Evidence(
        "syktyvkar", "syktyvkar-savin", "operator_listed",
        date(2026, 10, 11),
        "https://komidrama.ru/contacts",
        "Театр драмы имени Виктора Савина подтверждает адрес Первомайская, 56 "
        "и кассу, а афиша включает октябрь 2026 года. Свободный проход "
        "внутрь здания не подтверждён.",
    ),
    Evidence(
        "syktyvkar", "syktyvkar-opera", "operator_listed",
        date(2026, 10, 11),
        "https://komiopera.ru/kontakty/",
        "Контакты театра оперы и балета Коми подтверждают адрес "
        "Коммунистическая, 32 и часы работы КАССЫ, а не время "
        "открытого посещения зала. Билеты и доступ на спектакли "
        "необходимо уточнять отдельно.",
    ),
    Evidence(
        "syktyvkar", "syktyvkar-geology", "operator_listed",
        date(2026, 10, 11),
        "https://geo.komisc.ru/museum/museum-contacts",
        "Оператор — Институт геологии Коми НЦ УрО РАН — указывает музей "
        "Чернова на Первомайской, 54, часы и предварительную запись. "
        "Посещение без согласования не гарантируется.",
    ),
    Evidence(
        "syktyvkar", "syktyvkar-cathedral", "operator_listed",
        date(2026, 10, 11),
        ("https://syktyvkar-eparchia.ru/index/"
         "prikhoda_svjato_stefanovskogo_kafedralnogo_sobora/0-24"),
        "Сыктывкарская епархия указывает действующий кафедральный собор "
        "на Свободы, 60, контакт и обычное расписание богослужений. "
        "Праздничные ограничения и доступ на конкретную дату уточняйте.",
    ),
    Evidence(
        "ulan-ude", "ulan-ude-opera", "operator_listed",
        date(2026, 10, 11),
        "https://uuopera.ru/contacts/",
        "Бурятский театр оперы и балета указывает Ленина, 51 "
        "и часы работы кассы. Режим кассы не подтверждает вход "
        "в зрительный зал; наличие билетов уточняйте отдельно.",
    ),
    Evidence(
        "ulan-ude", "ulan-ude-history-museum", "operator_listed",
        date(2026, 10, 11),
        ("https://catalog.muzeyrb.ru/listing/"
         "музей-истории-бурятии-имени-м-н-хангал/"),
        "Национальный музей Бурятии указывает Музей истории имени "
        "М. Н. Хангалова на Профсоюзной, 29. Режим работы "
        "и экскурсионные условия на дату визита уточняйте.",
    ),
    Evidence(
        "ulan-ude", "ulan-ude-art-museum", "operator_listed",
        date(2026, 10, 11),
        "https://catalog.muzeyrb.ru/listing/художественный-музей/",
        "Каталог Национального музея Бурятии подтверждает "
        "Художественный музей Сампилова на Куйбышева, 29. "
        "Наличие конкретных экспозиций и билетов уточняйте.",
    ),
    Evidence(
        "ulan-ude", "ulan-ude-ethnographic", "operator_listed",
        date(2026, 10, 11),
        "https://xn--80akfjmebi8an4c6c.xn--p1ai/",
        "Сайт этнографического музея подтверждает Верхнюю Берёзовку, 17б, "
        "экспозиционные комплексы, сведения для посетителей и маршрут "
        "автобуса № 37. Время входа и сезонный доступ уточняйте.",
    ),
    # This is an official regional tourist-information listing, NOT the
    # attraction operator's own confirmation of hours or public access.
    Evidence(
        "omsk", "omsk-fortress", "official_tourism_listing",
        date(2026, 10, 11),
        "https://gotoomsk.ru/places/istoriko-kulturnyj-kompleks-omskaya-krepost/",
        "Туристский информационный центр Омской области описывает действующий "
        "исторический парк Омская крепость. Режим экскурсий уточняйте отдельно.",
    ),
    Evidence(
        "omsk", "tobolsk-gate-omsk", "official_tourism_listing",
        date(2026, 10, 11),
        "https://gotoomsk.ru/places/istoriko-kulturnyj-kompleks-omskaya-krepost/",
        "Туринфоцентр указывает Тобольские ворота как сохранившиеся подлинные "
        "ворота крепости. Доступ к ним на сегодня отдельно не подтверждён.",
    ),
    Evidence(
        "omsk", "tarsk-gate-omsk", "official_tourism_listing",
        date(2026, 10, 11),
        "https://gotoomsk.ru/places/istoriko-kulturnyj-kompleks-omskaya-krepost/",
        "Туринфоцентр сообщает: Тарские ворота снесены в 1959 году и "
        "восстановлены в 1991 году. Это реконструкция, а не исторический подлинник.",
    ),
    Evidence(
        "yaroslavl", "yar-volkov-theatre", "operator_listed",
        date(2026, 10, 11),
        "https://volkovteatr.ru/theatre/basic-information/",
        "Официальный сайт театра подтверждает действующее учреждение "
        "и его историческое здание; октябрьская афиша размещена на сайте.",
    ),
)


def evidence_for(city_slug: str, place_slug: str) -> Evidence | None:
    return next(
        (entry for entry in EVIDENCE
         if (entry.city_slug, entry.place_slug) == (city_slug, place_slug)),
        None,
    )


def public_evidence(
    city_slug: str, place_slug: str, *,
    as_of: date | None = None,
) -> dict:
    """A point-specific listing; never infer present-day, real-time accessibility."""
    now = datetime.now(UTC).date() if as_of is None else as_of
    entry = evidence_for(city_slug, place_slug)
    if entry is None:
        return {
            "status": "not_independently_checked",
            "checked_on": None,
            "evidence_url": None,
            "finding": "Нет актуального индивидуального подтверждения объекта.",
        }
    if (now - entry.checked_on).days > 90:
        return {
            "status": "evidence_stale",
            "checked_on": entry.checked_on.isoformat(),
            "evidence_url": entry.evidence_url,
            "finding": "Доказательство устарело; перепроверьте объект.",
        }
    return {
        "status": entry.status,
        "checked_on": entry.checked_on.isoformat(),
        "evidence_url": entry.evidence_url,
        "finding": entry.finding,
    }


def telegram_evidence_notice(
    city_slug: str, place_slug: str, *, as_of: date | None = None,
) -> str:
    """HTML-safe Telegram notice: source metadata != venue verified today."""
    evidence = public_evidence(city_slug, place_slug, as_of=as_of)
    status = evidence["status"]
    if status in {"operator_listed", "official_tourism_listing"}:
        date_text = escape(evidence["checked_on"] or "")
        evidence_link = escape(evidence["evidence_url"] or "", quote=True)
        source_label = (
            "сайте учреждения" if status == "operator_listed"
            else "сайте официального туристского инфоцентра"
        )
        return (
            f"📋 Объект указан на {source_label} ({date_text}): "
            f'<a href="{evidence_link}">подтверждающий источник</a>.'
            "\\n⚠️ Наличие места, часы и доступ в день посещения уточняйте."
        )
    if status == "evidence_stale":
        return (
            "⚠️ Прежнее подтверждение учреждения устарело. "
            "Фактическую доступность нужно перепроверить."
        )
    return (
        "⚠️ Существование и текущая доступность не подтверждены "
        "индивидуальной проверкой. Уточните перед поездкой."
    )


def validate_evidence(
    catalogs: tuple[CityCatalog, ...] | None = None, *,
    as_of: date | None = None,
) -> tuple[str, ...]:
    active = list_catalogs() if catalogs is None else catalogs
    known = {(c.slug, p.slug) for c in active for p in c.places}
    now = datetime.now(UTC).date() if as_of is None else as_of
    seen = set()
    errors = []
    for item in EVIDENCE:
        key = (item.city_slug, item.place_slug)
        if key in seen:
            errors.append(f"{key}: duplicate evidence")
        seen.add(key)
        if key not in known:
            errors.append(f"{key}: nonexistent or retired place")
        if item.status not in {"operator_listed", "official_tourism_listing"}:
            errors.append(f"{key}: unsupported evidence status")
        parsed = urlparse(item.evidence_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username:
            errors.append(f"{key}: invalid evidence URL")
        if item.checked_on > now:
            errors.append(f"{key}: evidence date in the future")
        if not item.finding.strip():
            errors.append(f"{key}: missing documentary finding")
    return tuple(errors)

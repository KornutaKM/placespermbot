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
    if status == "operator_listed":
        date_text = escape(evidence["checked_on"] or "")
        evidence_link = escape(evidence["evidence_url"] or "", quote=True)
        return (
            f"📋 Объект указан на сайте учреждения ({date_text}): "
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
        if item.status != "operator_listed":
            errors.append(f"{key}: unsupported evidence status")
        parsed = urlparse(item.evidence_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username:
            errors.append(f"{key}: invalid evidence URL")
        if item.checked_on > now:
            errors.append(f"{key}: evidence date in the future")
        if not item.finding.strip():
            errors.append(f"{key}: missing documentary finding")
    return tuple(errors)

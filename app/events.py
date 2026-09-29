from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from urllib.parse import urlparse

from app.config import Settings

SOURCE_CHECKED_AT = date(2026, 9, 29)

YANDEX_AFISHA_URL = "https://afisha.yandex.ru/saint-petersburg/events"
KUDAGO_EVENTS_URL = "https://kudago.com/spb/events/"


@dataclass(frozen=True, slots=True)
class EventProvider:
    provider_id: str
    name: str
    catalog_url: str
    source_url: str
    checked_at: date
    integration_mode: str
    note: str


def get_event_providers(settings: Settings) -> tuple[EventProvider, ...]:
    return (
        EventProvider(
            provider_id="yandex-afisha",
            name="Яндекс Афиша",
            catalog_url=_safe_provider_url(
                settings.yandex_afisha_url,
                fallback=YANDEX_AFISHA_URL,
                allowed_hosts={"afisha.yandex.ru"},
            ),
            source_url=YANDEX_AFISHA_URL,
            checked_at=SOURCE_CHECKED_AT,
            integration_mode="catalog-link",
            note=(
                "Актуальные даты, билеты и цены проверяются "
                "на стороне Яндекс Афиши."
            ),
        ),
        EventProvider(
            provider_id="kudago",
            name="KudaGo",
            catalog_url=_safe_provider_url(
                settings.kudago_events_url,
                fallback=KUDAGO_EVENTS_URL,
                allowed_hosts={"kudago.com", "www.kudago.com"},
            ),
            source_url=KUDAGO_EVENTS_URL,
            checked_at=SOURCE_CHECKED_AT,
            integration_mode="catalog-link",
            note=(
                "Актуальные даты, билеты и цены проверяются "
                "на стороне KudaGo."
            ),
        ),
    )


def _safe_provider_url(
    candidate: str,
    *,
    fallback: str,
    allowed_hosts: set[str],
) -> str:
    value = candidate.strip()
    if not value:
        return fallback

    parsed = urlparse(value)
    host = (parsed.hostname or "").casefold()

    if parsed.scheme != "https" or host not in allowed_hosts:
        return fallback

    return value

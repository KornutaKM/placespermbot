from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from urllib.parse import urlparse

from app.config import Settings

SOURCE_CHECKED_AT = date(2026, 9, 29)

SPUTNIK8_CATALOG_URL = "https://www.sputnik8.com/ru/st-petersburg"
TRIPSTER_CATALOG_URL = "https://experience.tripster.ru/experience/Saint_Petersburg/"


@dataclass(frozen=True, slots=True)
class ExcursionProvider:
    provider_id: str
    name: str
    catalog_url: str
    source_url: str
    checked_at: date
    integration_mode: str
    note: str


def get_excursion_providers(
    settings: Settings,
    *,
    city_slug: str = "saint-petersburg",
) -> tuple[ExcursionProvider, ...]:
    if city_slug != "saint-petersburg":
        return ()

    return (
        ExcursionProvider(
            provider_id="sputnik8",
            name="Sputnik8",
            catalog_url=_safe_provider_url(
                settings.sputnik8_affiliate_url,
                fallback=SPUTNIK8_CATALOG_URL,
                allowed_hosts={"sputnik8.com", "www.sputnik8.com"},
            ),
            source_url=SPUTNIK8_CATALOG_URL,
            checked_at=SOURCE_CHECKED_AT,
            integration_mode="catalog-link",
            note=(
                "Актуальные цены, расписание и доступность проверяются "
                "на стороне Sputnik8."
            ),
        ),
        ExcursionProvider(
            provider_id="tripster",
            name="Tripster",
            catalog_url=_safe_provider_url(
                settings.tripster_affiliate_url,
                fallback=TRIPSTER_CATALOG_URL,
                allowed_hosts={"tripster.ru", "www.tripster.ru", "experience.tripster.ru"},
            ),
            source_url=TRIPSTER_CATALOG_URL,
            checked_at=SOURCE_CHECKED_AT,
            integration_mode="catalog-link",
            note=(
                "Актуальные цены, расписание и доступность проверяются "
                "на стороне Tripster."
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

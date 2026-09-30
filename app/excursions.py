from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from urllib.parse import urlparse

from app.config import Settings

SOURCE_CHECKED_AT = date(2026, 9, 30)

SPUTNIK8_CATALOG_URL = "https://www.sputnik8.com/ru/st-petersburg"
TRIPSTER_CATALOG_URL = "https://experience.tripster.ru/experience/Saint_Petersburg/"
PERM_SPUTNIK8_CATALOG_URL = "https://www.sputnik8.com/ru/perm"
PERM_TRIPSTER_CATALOG_URL = "https://experience.tripster.ru/experience/Perm/"


@dataclass(frozen=True, slots=True)
class ExcursionProvider:
    provider_id: str
    name: str
    catalog_url: str
    source_url: str
    checked_at: date
    integration_mode: str
    note: str


@dataclass(frozen=True, slots=True)
class ExcursionCityConfig:
    sputnik8_url: str
    tripster_url: str
    sputnik8_override_attr: str
    tripster_override_attr: str


_CITY_CONFIGS: dict[str, ExcursionCityConfig] = {
    "saint-petersburg": ExcursionCityConfig(
        sputnik8_url=SPUTNIK8_CATALOG_URL,
        tripster_url=TRIPSTER_CATALOG_URL,
        sputnik8_override_attr="sputnik8_affiliate_url",
        tripster_override_attr="tripster_affiliate_url",
    ),
    "perm": ExcursionCityConfig(
        sputnik8_url=PERM_SPUTNIK8_CATALOG_URL,
        tripster_url=PERM_TRIPSTER_CATALOG_URL,
        sputnik8_override_attr="sputnik8_perm_affiliate_url",
        tripster_override_attr="tripster_perm_affiliate_url",
    ),
}


def get_excursion_providers(
    settings: Settings,
    *,
    city_slug: str = "saint-petersburg",
) -> tuple[ExcursionProvider, ...]:
    config = _CITY_CONFIGS.get(city_slug)
    if config is None:
        return ()

    return (
        ExcursionProvider(
            provider_id="sputnik8",
            name="Sputnik8",
            catalog_url=_safe_provider_url(
                str(getattr(settings, config.sputnik8_override_attr)),
                fallback=config.sputnik8_url,
                allowed_hosts={"sputnik8.com", "www.sputnik8.com"},
            ),
            source_url=config.sputnik8_url,
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
                str(getattr(settings, config.tripster_override_attr)),
                fallback=config.tripster_url,
                allowed_hosts={
                    "tripster.ru",
                    "www.tripster.ru",
                    "experience.tripster.ru",
                },
            ),
            source_url=config.tripster_url,
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

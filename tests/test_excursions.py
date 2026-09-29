from datetime import date

from app.config import Settings
from app.excursions import (
    SPUTNIK8_CATALOG_URL,
    TRIPSTER_CATALOG_URL,
    get_excursion_providers,
)
from app.keyboards import excursion_providers_keyboard


def test_default_providers_use_official_live_catalogs() -> None:
    providers = get_excursion_providers(Settings())
    by_id = {provider.provider_id: provider for provider in providers}

    assert by_id["sputnik8"].catalog_url == SPUTNIK8_CATALOG_URL
    assert by_id["tripster"].catalog_url == TRIPSTER_CATALOG_URL
    assert all(provider.integration_mode == "catalog-link" for provider in providers)
    assert all(provider.checked_at == date(2026, 9, 29) for provider in providers)


def test_same_host_https_affiliate_override_is_allowed() -> None:
    settings = Settings(
        sputnik8_affiliate_url=(
            "https://www.sputnik8.com/ru/st-petersburg?utm_source=placesbot"
        ),
        tripster_affiliate_url=(
            "https://experience.tripster.ru/experience/Saint_Petersburg/"
            "?utm_source=placesbot"
        ),
    )
    providers = get_excursion_providers(settings)
    by_id = {provider.provider_id: provider for provider in providers}

    assert "utm_source=placesbot" in by_id["sputnik8"].catalog_url
    assert "utm_source=placesbot" in by_id["tripster"].catalog_url


def test_unsafe_affiliate_override_falls_back_to_official_url() -> None:
    settings = Settings(
        sputnik8_affiliate_url="http://www.sputnik8.com/ru/st-petersburg",
        tripster_affiliate_url="https://example.com/fake-tripster",
    )
    providers = get_excursion_providers(settings)
    by_id = {provider.provider_id: provider for provider in providers}

    assert by_id["sputnik8"].catalog_url == SPUTNIK8_CATALOG_URL
    assert by_id["tripster"].catalog_url == TRIPSTER_CATALOG_URL


def test_provider_keyboard_contains_direct_urls_and_home_action() -> None:
    providers = get_excursion_providers(Settings())
    markup = excursion_providers_keyboard(providers)

    urls = {
        button.url
        for row in markup.inline_keyboard
        for button in row
        if button.url is not None
    }
    callbacks = {
        button.callback_data
        for row in markup.inline_keyboard
        for button in row
        if button.callback_data is not None
    }

    assert urls == {provider.catalog_url for provider in providers}
    assert "menu:home" in callbacks


def test_provider_records_keep_source_provenance_separate_from_affiliate_url() -> None:
    settings = Settings(
        sputnik8_affiliate_url=(
            "https://www.sputnik8.com/ru/st-petersburg?partner=placesbot"
        )
    )
    providers = get_excursion_providers(settings)
    sputnik8 = next(
        provider for provider in providers if provider.provider_id == "sputnik8"
    )

    assert sputnik8.catalog_url != sputnik8.source_url
    assert sputnik8.source_url == SPUTNIK8_CATALOG_URL

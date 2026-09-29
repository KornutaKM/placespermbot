from datetime import date

from app.config import Settings
from app.events import (
    KUDAGO_EVENTS_URL,
    YANDEX_AFISHA_URL,
    get_event_providers,
)
from app.keyboards import event_providers_keyboard


def test_default_event_providers_use_live_catalogs() -> None:
    providers = get_event_providers(Settings())
    by_id = {provider.provider_id: provider for provider in providers}

    assert by_id["yandex-afisha"].catalog_url == YANDEX_AFISHA_URL
    assert by_id["kudago"].catalog_url == KUDAGO_EVENTS_URL
    assert all(provider.integration_mode == "catalog-link" for provider in providers)
    assert all(provider.checked_at == date(2026, 9, 29) for provider in providers)


def test_same_host_https_event_override_is_allowed() -> None:
    settings = Settings(
        yandex_afisha_url=(
            "https://afisha.yandex.ru/saint-petersburg/events?preset=today"
        ),
        kudago_events_url="https://kudago.com/spb/events/?utm_source=placesbot",
    )
    providers = get_event_providers(settings)
    by_id = {provider.provider_id: provider for provider in providers}

    assert "preset=today" in by_id["yandex-afisha"].catalog_url
    assert "utm_source=placesbot" in by_id["kudago"].catalog_url


def test_unsafe_event_override_falls_back_to_official_url() -> None:
    settings = Settings(
        yandex_afisha_url="http://afisha.yandex.ru/saint-petersburg/events",
        kudago_events_url="https://example.com/spb/events/",
    )
    providers = get_event_providers(settings)
    by_id = {provider.provider_id: provider for provider in providers}

    assert by_id["yandex-afisha"].catalog_url == YANDEX_AFISHA_URL
    assert by_id["kudago"].catalog_url == KUDAGO_EVENTS_URL


def test_event_provider_keyboard_contains_urls_and_home_action() -> None:
    providers = get_event_providers(Settings())
    markup = event_providers_keyboard(providers)

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

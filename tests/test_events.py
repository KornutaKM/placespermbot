from datetime import date

from app.config import Settings
from app.events import (
    KUDAGO_EVENTS_URL,
    PERM_YANDEX_AFISHA_URL,
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
    assert all(provider.checked_at == date(2026, 9, 30) for provider in providers)


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



def test_perm_events_use_only_verified_yandex_catalog() -> None:
    providers = get_event_providers(Settings(), city_slug="perm")

    assert len(providers) == 1
    assert providers[0].provider_id == "yandex-afisha"
    assert providers[0].catalog_url == PERM_YANDEX_AFISHA_URL
    assert providers[0].checked_at == date(2026, 9, 30)


def test_event_overrides_are_city_scoped() -> None:
    settings = Settings(
        yandex_afisha_url=(
            "https://afisha.yandex.ru/saint-petersburg/events?source=spb"
        ),
        yandex_afisha_perm_url="https://afisha.yandex.ru/perm?source=perm",
    )

    spb = get_event_providers(settings, city_slug="saint-petersburg")
    perm = get_event_providers(settings, city_slug="perm")

    spb_yandex = next(item for item in spb if item.provider_id == "yandex-afisha")
    assert "source=spb" in spb_yandex.catalog_url
    assert "source=perm" in perm[0].catalog_url
    assert all(item.provider_id != "kudago" for item in perm)


def test_unsafe_perm_event_override_falls_back() -> None:
    settings = Settings(
        yandex_afisha_perm_url="https://example.com/perm",
    )
    providers = get_event_providers(settings, city_slug="perm")

    assert providers[0].catalog_url == PERM_YANDEX_AFISHA_URL


def test_unknown_city_events_remain_fail_closed() -> None:
    assert get_event_providers(Settings(), city_slug="unknown-city") == ()

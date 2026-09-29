from app.catalog import get_catalog
from app.config import Settings
from app.data.spb import CITY_SLUG
from app.events import get_event_providers
from app.excursions import get_excursion_providers
from app.keyboards import (
    event_providers_keyboard,
    excursion_providers_keyboard,
    generated_route_keyboard,
    home_keyboard,
    interests_keyboard,
    paginated_places_keyboard,
    personalized_places_keyboard,
    request_location_keyboard,
    route_details_keyboard,
    route_duration_keyboard,
    route_interest_keyboard,
)
from app.pagination import paginate
from app.planner import INTEREST_LABELS, build_route


def callback_values(markup) -> set[str]:
    return {
        button.callback_data
        for row in markup.inline_keyboard
        for button in row
        if button.callback_data is not None
    }


def test_home_exposes_route_builder() -> None:
    assert "builder:start" in callback_values(home_keyboard())


def test_duration_keyboard_contains_supported_budgets() -> None:
    callbacks = callback_values(route_duration_keyboard())

    assert "builder:duration:120" in callbacks
    assert "builder:duration:240" in callbacks
    assert "builder:duration:360" in callbacks


def test_interest_keyboard_contains_all_supported_interests() -> None:
    callbacks = callback_values(route_interest_keyboard())

    for interest in INTEREST_LABELS:
        assert f"builder:interest:{interest}" in callbacks


def test_generated_route_points_open_place_cards() -> None:
    catalog = get_catalog(CITY_SLUG)
    route = build_route(catalog, budget_minutes=240, interest="classic")

    assert route is not None
    callbacks = callback_values(generated_route_keyboard(route.places))

    for place in route.places:
        assert f"place:{place.slug}" in callbacks
    assert "builder:start" in callbacks


def test_duration_keyboard_offers_location_origin() -> None:
    assert "builder:location" in callback_values(route_duration_keyboard())


def test_location_keyboard_requests_native_telegram_location() -> None:
    markup = request_location_keyboard()
    location_button = markup.keyboard[0][0]

    assert location_button.request_location is True
    assert any(button.text == "Отмена" for row in markup.keyboard for button in row)


def url_values(markup) -> set[str]:
    return {
        button.url
        for row in markup.inline_keyboard
        for button in row
        if button.url is not None
    }


def test_generated_route_exposes_google_maps_url() -> None:
    city = get_catalog(CITY_SLUG)
    route = build_route(city, budget_minutes=240, interest="classic")

    assert route is not None
    urls = url_values(generated_route_keyboard(route.places))

    assert urls
    assert all(url.startswith("https://www.google.com/maps/") for url in urls)


def test_editorial_route_keyboard_exposes_google_maps_url() -> None:
    city = get_catalog(CITY_SLUG)
    route = city.routes[0]
    places = tuple(
        place
        for slug in route.place_slugs
        if (place := city.place_by_slug(slug)) is not None
    )

    urls = url_values(route_details_keyboard(places))

    assert urls


def test_home_exposes_near_me_action() -> None:
    assert "menu:nearby" in callback_values(home_keyboard())


def test_excursion_provider_keyboard_has_live_urls() -> None:
    providers = get_excursion_providers(Settings())
    urls = url_values(excursion_providers_keyboard(providers))

    assert urls == {provider.catalog_url for provider in providers}


def test_home_exposes_events_action() -> None:
    assert "menu:events" in callback_values(home_keyboard())


def test_event_provider_keyboard_has_live_urls() -> None:
    providers = get_event_providers(Settings())
    urls = url_values(event_providers_keyboard(providers))

    assert urls == {provider.catalog_url for provider in providers}


def test_home_exposes_personalized_action() -> None:
    assert "menu:personal" in callback_values(home_keyboard())


def test_interests_keyboard_contains_all_supported_interests() -> None:
    callbacks = callback_values(interests_keyboard(("museums", "free")))

    for interest in INTEREST_LABELS:
        assert f"pref:toggle:{interest}" in callbacks
    assert "pref:done" in callbacks


def test_personalized_places_open_cards_and_preferences() -> None:
    city = get_catalog(CITY_SLUG)
    page = paginate(city.places[:8], 0)
    callbacks = callback_values(personalized_places_keyboard(page))

    for place in page.items:
        assert f"place:{place.slug}" in callbacks
    assert "pref:edit" in callbacks
    assert "personalpage:1" in callbacks


def test_paginated_places_keyboard_limits_rows_and_has_navigation() -> None:
    city = get_catalog(CITY_SLUG)
    page = paginate(city.places[:14], 1)
    markup = paginated_places_keyboard(
        page,
        page_callback_prefix="catpage:museums",
        back_callback="menu:places",
        back_text="← Категории",
    )
    callbacks = callback_values(markup)
    place_callbacks = {value for value in callbacks if value.startswith("place:")}

    assert len(place_callbacks) <= 6
    assert "catpage:museums:0" in callbacks
    assert "catpage:museums:2" in callbacks
    assert "noop" in callbacks

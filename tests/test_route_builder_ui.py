from app.catalog import get_catalog, list_catalogs
from app.config import Settings
from app.data.spb import CITY_SLUG
from app.events import get_event_providers
from app.excursions import get_excursion_providers
from app.keyboards import (
    cities_keyboard,
    event_providers_keyboard,
    excursion_providers_keyboard,
    generated_route_keyboard,
    home_keyboard,
    interests_keyboard,
    paginated_places_keyboard,
    personalized_places_keyboard,
    place_keyboard,
    profile_keyboard,
    request_location_keyboard,
    route_details_keyboard,
    route_duration_keyboard,
    route_interest_keyboard,
    saved_route_details_keyboard,
    saved_routes_keyboard,
    visited_places_keyboard,
)
from app.navigation import (
    category_context,
    personal_context,
    place_callback,
    route_context,
    saved_route_context,
    visited_context,
)
from app.pagination import paginate
from app.planner import INTEREST_LABELS, build_route
from app.saved_routes import SavedRoute, build_save_callback


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
    save_callback = build_save_callback(catalog, route)
    callbacks = callback_values(
        generated_route_keyboard(
            route.places,
            save_callback=save_callback,
        )
    )

    for place in route.places:
        assert place_callback(place.slug, route_context()) in callbacks
    assert save_callback in callbacks
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
        assert place_callback(place.slug, personal_context(page.index)) in callbacks
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
        place_context=category_context("museums", page.index),
    )
    callbacks = callback_values(markup)
    place_callbacks = {value for value in callbacks if value.startswith("place:")}

    assert len(place_callbacks) <= 6
    for place in page.items:
        assert place_callback(
            place.slug,
            category_context("museums", page.index),
        ) in callbacks
    assert "catpage:museums:0" in callbacks
    assert "catpage:museums:2" in callbacks
    assert "noop" in callbacks


def test_place_keyboard_exposes_walking_directions_url() -> None:
    place = get_catalog(CITY_SLUG).places[0]
    markup = place_keyboard(place)
    urls = url_values(markup)

    assert len(urls) == 1
    url = next(iter(urls))
    assert url.startswith("https://www.google.com/maps/dir/")


def test_place_keyboard_preserves_category_context_for_actions_and_back() -> None:
    place = get_catalog(CITY_SLUG).places[0]
    markup = place_keyboard(place, context="c.sights.2")
    callbacks = callback_values(markup)

    assert f"nearby:{place.slug}|c.sights.2" in callbacks
    assert f"favorite:add:{place.slug}|c.sights.2" in callbacks
    assert "catpage:sights:2" in callbacks


def test_home_exposes_city_selector() -> None:
    assert "menu:cities" in callback_values(home_keyboard())


def test_city_selector_marks_current_catalog() -> None:
    catalogs = list_catalogs()
    current = catalogs[0]
    markup = cities_keyboard(catalogs, current.slug)
    callbacks = callback_values(markup)

    assert f"city:set:{current.slug}" in callbacks
    assert "menu:home" in callbacks

    selected_buttons = [
        button
        for row in markup.inline_keyboard
        for button in row
        if button.callback_data == f"city:set:{current.slug}"
    ]
    assert selected_buttons
    assert selected_buttons[0].text.startswith("✅ ")


def test_live_providers_fail_closed_for_unsupported_city() -> None:
    assert get_excursion_providers(
        Settings(),
        city_slug="unsupported-city",
    ) == ()
    assert get_event_providers(
        Settings(),
        city_slug="unsupported-city",
    ) == ()


def test_home_exposes_visited_history() -> None:
    assert "menu:visited" in callback_values(home_keyboard())


def test_place_keyboard_exposes_visited_toggle_and_preserves_context() -> None:
    place = get_catalog(CITY_SLUG).places[0]
    markup = place_keyboard(
        place,
        is_favorite=True,
        is_visited=False,
        context="c.sights.2",
    )
    callbacks = callback_values(markup)

    assert f"visit:add:{place.slug}|c.sights.2" in callbacks
    assert f"favorite:remove:{place.slug}|c.sights.2" in callbacks

    visited_markup = place_keyboard(
        place,
        is_favorite=True,
        is_visited=True,
        context="v.1",
    )
    visited_callbacks = callback_values(visited_markup)

    assert f"visit:remove:{place.slug}|v.1" in visited_callbacks
    assert "visitedpage:1" in visited_callbacks


def test_visited_history_keyboard_preserves_page_context() -> None:
    city = get_catalog(CITY_SLUG)
    page = paginate(city.places[:8], 1)
    callbacks = callback_values(visited_places_keyboard(page))

    for place in page.items:
        assert place_callback(
            place.slug,
            visited_context(page.index),
        ) in callbacks
    assert "visitedpage:0" in callbacks


def test_home_exposes_profile() -> None:
    assert "menu:profile" in callback_values(home_keyboard())


def test_profile_keyboard_links_existing_user_flows() -> None:
    callbacks = callback_values(profile_keyboard())

    assert callbacks == {
        "menu:cities",
        "pref:edit",
        "menu:favorites",
        "menu:visited",
        "menu:savedroutes",
        "menu:home",
    }


def test_saved_routes_keyboard_opens_saved_route() -> None:
    route = SavedRoute(
        route_id="abc123",
        city_slug=CITY_SLUG,
        interest="museums",
        budget_minutes=240,
        place_slugs=("hermitage",),
        created_at="2026-09-29 12:00:00",
    )
    page = paginate((route,), 0)
    callbacks = callback_values(saved_routes_keyboard(page))

    assert "savedroute:abc123" in callbacks
    assert "menu:profile" in callbacks


def test_saved_route_details_preserve_route_context() -> None:
    catalog = get_catalog(CITY_SLUG)
    route = SavedRoute(
        route_id="abc123",
        city_slug=CITY_SLUG,
        interest="classic",
        budget_minutes=240,
        place_slugs=tuple(place.slug for place in catalog.places[:2]),
        created_at="2026-09-29 12:00:00",
    )
    places = catalog.places[:2]
    callbacks = callback_values(saved_route_details_keyboard(route, places))

    for place in places:
        assert place_callback(
            place.slug,
            saved_route_context(route.route_id),
        ) in callbacks
    assert "savedroute:delete:abc123" in callbacks
    assert "menu:savedroutes" in callbacks

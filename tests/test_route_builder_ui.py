from app.catalog import get_catalog
from app.data.spb import CITY_SLUG
from app.keyboards import (
    generated_route_keyboard,
    home_keyboard,
    route_duration_keyboard,
    route_interest_keyboard,
)
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

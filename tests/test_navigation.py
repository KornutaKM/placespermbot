import pytest

from app.catalog import get_catalog
from app.data.spb import CITY_SLUG
from app.navigation import (
    TELEGRAM_CALLBACK_MAX_BYTES,
    back_target,
    category_context,
    dismissed_callback,
    favorite_callback,
    favorites_context,
    nearby_child_context,
    parse_dismissed_callback,
    parse_favorite_callback,
    parse_place_callback,
    parse_visited_callback,
    personal_context,
    place_callback,
    saved_route_context,
    visited_callback,
    visited_context,
)


def test_category_context_round_trip() -> None:
    context = category_context("museums", 2)
    callback = place_callback("hermitage", context)

    assert parse_place_callback(callback) == ("hermitage", "c.museums.2")
    assert back_target(context).callback_data == "catpage:museums:2"


def test_favorites_context_returns_same_page() -> None:
    context = favorites_context(3)

    assert back_target(context).callback_data == "favpage:3"
    assert back_target(context).text == "← Избранное"


def test_personal_context_returns_same_page() -> None:
    context = personal_context(1)

    assert back_target(context).callback_data == "personalpage:1"
    assert back_target(context).text == "← Для меня"


def test_visited_context_returns_same_page() -> None:
    context = visited_context(4)

    assert back_target(context).callback_data == "visitedpage:4"
    assert back_target(context).text == "← Посещённые"


def test_dismissed_action_preserves_context() -> None:
    callback = dismissed_callback("add", "hermitage", "p.2")

    assert parse_dismissed_callback(callback) == (
        "add",
        "hermitage",
        "p.2",
    )


def test_visited_action_preserves_context() -> None:
    callback = visited_callback("add", "hermitage", "v.2")

    assert parse_visited_callback(callback) == (
        "add",
        "hermitage",
        "v.2",
    )




def test_saved_route_context_returns_to_exact_route() -> None:
    context = saved_route_context("abc123def456")
    target = back_target(context)

    assert context == "z.abc123def456"
    assert target.callback_data == "savedroute:abc123def456"
    assert target.text == "← Сохранённый маршрут"


def test_old_place_callback_remains_compatible() -> None:
    assert parse_place_callback("place:hermitage") == ("hermitage", "d")
    assert back_target("d").callback_data == "menu:places"


def test_favorite_action_preserves_context() -> None:
    callback = favorite_callback("add", "hermitage", "c.museums.1")

    assert parse_favorite_callback(callback) == (
        "add",
        "hermitage",
        "c.museums.1",
    )


def test_nearby_child_returns_to_origin_with_parent_context() -> None:
    context = nearby_child_context("palace-square", "c.sights.1")
    target = back_target(context)

    assert target.callback_data == "place:palace-square|c.sights.1"
    assert target.text == "← К исходному месту"


def test_unknown_context_falls_back_to_categories() -> None:
    target = back_target("unknown")

    assert target.callback_data == "menu:places"
    assert target.text == "← Категории"


def test_malformed_context_is_normalized_to_default() -> None:
    callback = place_callback("hermitage", "bad:context")

    assert callback == "place:hermitage|d"


def test_current_catalog_callbacks_fit_telegram_limit() -> None:
    catalog = get_catalog(CITY_SLUG)

    for place in catalog.places:
        for context in (
            category_context("museums", 99),
            favorites_context(99),
            personal_context(99),
            visited_context(99),
            saved_route_context("0123456789abcdef"),
            nearby_child_context("peter-paul-fortress", "c.sights.9"),
        ):
            callback = place_callback(place.slug, context)
            assert len(callback.encode("utf-8")) <= TELEGRAM_CALLBACK_MAX_BYTES

        visited = visited_callback("add", place.slug, visited_context(99))
        assert len(visited.encode("utf-8")) <= TELEGRAM_CALLBACK_MAX_BYTES

        dismissed = dismissed_callback("add", place.slug, personal_context(99))
        assert len(dismissed.encode("utf-8")) <= TELEGRAM_CALLBACK_MAX_BYTES


def test_oversized_callback_fails_closed() -> None:
    with pytest.raises(ValueError, match="64-byte"):
        place_callback("x" * 63, "d")

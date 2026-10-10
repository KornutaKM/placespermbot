import asyncio
from dataclasses import replace
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.catalog import get_catalog, list_catalogs
from app.database import migrate_database
from app.domain import Place, PlaceSource
from app.handlers.main import (
    cancel_generated_route_stop_edit,
    remove_generated_route_stop,
    save_generated_route,
    show_generated_route_stop_editor,
)
from app.keyboards import generated_route_keyboard
from app.planner import MAX_GENERATED_WALK_LEG_KM, build_route
from app.route_edit import (
    back_callback,
    edit_callback,
    parse_editor_callback,
    parse_remove_callback,
    remove_callback,
    route_after_removal,
)
from app.route_timing import route_timing
from app.saved_routes import RouteSnapshot, build_save_callback, parse_save_callback
from app.storage import SavedRoutesRepository


class FakeMessage:
    def __init__(self):
        self.edits = []
        self.markups = []

    async def edit_text(self, text, *, reply_markup=None):
        self.edits.append((text, reply_markup))

    async def edit_reply_markup(self, *, reply_markup=None):
        self.markups.append(reply_markup)


class FakeCallback:
    def __init__(self, user_id, data):
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.message = FakeMessage()
        self.answers = []

    async def answer(self, text=None, *, show_alert=False):
        self.answers.append((text, show_alert))


def callbacks(markup):
    return {
        button.callback_data
        for row in markup.inline_keyboard
        for button in row
        if button.callback_data is not None
    }


def test_edit_callbacks_stay_within_telegram_limit_for_all_cities():
    for catalog in list_catalogs():
        route = build_route(catalog, budget_minutes=360, interest="classic")
        assert route is not None
        save = build_save_callback(catalog, route)
        assert len(save.encode("utf-8")) <= 64
        if len(route.places) < 2:
            continue
        assert len(edit_callback(save).encode("utf-8")) <= 64
        assert len(back_callback(save).encode("utf-8")) <= 64
        assert parse_editor_callback(edit_callback(save), catalog).places == route.places
        assert parse_editor_callback(back_callback(save), catalog).places == route.places
        for index in range(len(route.places)):
            data = remove_callback(save, index)
            assert len(data.encode("utf-8")) <= 64
            snapshot, decoded = parse_remove_callback(data, catalog)
            assert decoded == index
            assert snapshot.places == route.places


def test_edit_stop_recalculates_valid_routes_without_reordering():
    for catalog in list_catalogs():
        route = build_route(catalog, budget_minutes=240, interest="classic")
        assert route is not None
        if len(route.places) < 2:
            continue
        snapshot = parse_save_callback(build_save_callback(catalog, route), catalog)
        for index in (0, len(route.places) - 1):
            edited = route_after_removal(snapshot, index)
            expected = route.places[:index] + route.places[index + 1 :]
            assert edited.places == expected
            assert edited.estimated_minutes <= route.budget_minutes
            assert route_timing(edited).walking_minutes >= 0
            assert len(set(p.slug for p in edited.places)) == len(edited.places)
            assert edited.distance_km <= route.distance_km + 0.1


def test_edit_rejects_catalog_reorder_tampering_and_bad_indices():
    catalog = get_catalog("saint-petersburg")
    route = build_route(catalog, budget_minutes=240, interest="classic")
    assert route is not None
    save = build_save_callback(catalog, route)
    changed = replace(catalog, places=tuple(reversed(catalog.places)))
    with pytest.raises(ValueError, match="checksum"):
        parse_editor_callback(edit_callback(save), changed)
    with pytest.raises(ValueError, match="checksum"):
        parse_remove_callback(remove_callback(save, 0), changed)
    with pytest.raises(ValueError, match="out of bounds"):
        parse_remove_callback(remove_callback(save, 255), catalog)
    for malformed in ("dropg:", "dropg:zz", "dropg:x0garbage"):
        with pytest.raises(ValueError):
            parse_remove_callback(malformed, catalog)


def test_edit_rejects_unsafe_new_bridge_and_single_stop():
    source = PlaceSource("Test", "https://example.org/", date(2026, 10, 1))
    places = tuple(
        Place(
            slug=f"p{index}",
            title=f"Point {index}",
            category="sights",
            summary="Test",
            emoji="🏛",
            district="centre",
            visit_minutes=20,
            is_free=True,
            latitude=55.0 + index * 0.035,
            longitude=37.0,
            source=source,
        )
        for index in range(3)
    )
    from app.catalog import distance_km

    assert distance_km(places[0], places[1]) < MAX_GENERATED_WALK_LEG_KM
    assert distance_km(places[1], places[2]) < MAX_GENERATED_WALK_LEG_KM
    assert distance_km(places[0], places[2]) > MAX_GENERATED_WALK_LEG_KM

    snapshot = RouteSnapshot(interest="classic", budget_minutes=240, places=places)
    with pytest.raises(ValueError, match="long walking leg"):
        route_after_removal(snapshot, 1)
    single = RouteSnapshot(interest="classic", budget_minutes=120, places=(places[0],))
    with pytest.raises(ValueError, match="At least one"):
        route_after_removal(single, 0)
    with pytest.raises(ValueError, match="out of bounds"):
        route_after_removal(snapshot, -1)
    with pytest.raises(ValueError, match="time budget"):
        route_after_removal(replace(snapshot, budget_minutes=20), 0)


def test_generated_keyboard_only_offers_editor_when_enabled():
    catalog = get_catalog("saint-petersburg")
    route = build_route(catalog, budget_minutes=240, interest="classic")
    assert route is not None and len(route.places) >= 2
    save = build_save_callback(catalog, route)
    assert edit_callback(save) not in callbacks(
        generated_route_keyboard(route.places, save_callback=save)
    )
    assert edit_callback(save) in callbacks(
        generated_route_keyboard(route.places, save_callback=save, allow_edit=True)
    )

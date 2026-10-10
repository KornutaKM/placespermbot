import asyncio
from types import SimpleNamespace
from unittest.mock import patch

from app.catalog import get_catalog
from app.database import migrate_database
from app.handlers.main import (
    RouteBuilderFlow,
    route_builder_duration,
    route_builder_interest,
    route_builder_location,
    route_builder_request_location,
    route_builder_start,
    route_builder_toggle_visited,
)
from app.keyboards import route_duration_keyboard
from app.navigation import parse_place_callback
from app.planner import build_route
from app.storage import VisitedRepository


class FakeState:
    def __init__(self):
        self.status = None
        self.data = {}

    async def get_state(self):
        return self.status

    async def set_state(self, status):
        self.status = status.state if hasattr(status, "state") else status

    async def clear(self):
        self.status = None
        self.data = {}

    async def update_data(self, **changes):
        self.data.update(changes)

    async def get_data(self):
        return dict(self.data)


class FakeMessage:
    def __init__(self, location=None):
        self.location = location
        self.edits = []
        self.markup_edits = []
        self.answers = []

    async def edit_text(self, text, *, reply_markup=None):
        self.edits.append((text, reply_markup))

    async def edit_reply_markup(self, *, reply_markup=None):
        self.markup_edits.append(reply_markup)

    async def answer(self, text, *, reply_markup=None):
        self.answers.append((text, reply_markup))


class FakeCallback:
    def __init__(self, user_id, data):
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.message = FakeMessage()
        self.answers = []

    async def answer(self, text=None, *, show_alert=False):
        self.answers.append((text, show_alert))


def callback_values(markup):
    return {
        button.callback_data
        for row in markup.inline_keyboard
        for button in row
        if button.callback_data is not None
    }


def test_builder_exclusion_is_explicit_and_default_off():
    catalog = get_catalog("perm")
    baseline = build_route(catalog, budget_minutes=240, interest="classic")
    assert baseline is not None
    selected = baseline.places[0].slug

    unchanged = build_route(
        catalog,
        budget_minutes=240,
        interest="classic",
        excluded_slugs=(),
    )
    filtered = build_route(
        catalog,
        budget_minutes=240,
        interest="classic",
        excluded_slugs=(selected,),
    )
    assert baseline == unchanged
    assert filtered is not None
    assert selected not in {place.slug for place in filtered.places}
    assert filtered.estimated_minutes <= filtered.budget_minutes

    assert "builder:visited:toggle" in callback_values(route_duration_keyboard())
    assert "builder:visited:toggle" in callback_values(
        route_duration_keyboard(exclude_visited=True)
    )


def test_builder_toggle_round_trip_and_stale_callback():
    async def scenario():
        state = FakeState()
        start = FakeCallback(42, "builder:start")
        await route_builder_start(start, state)
        assert await state.get_state() == RouteBuilderFlow.waiting_duration.state

        first = FakeCallback(42, "builder:visited:toggle")
        await route_builder_toggle_visited(first, state)
        assert (await state.get_data())["exclude_visited"] is True
        assert any(
            button.text == "✅ Посещённые исключены"
            for row in first.message.markup_edits[0].inline_keyboard
            for button in row
        )

        again = FakeCallback(42, "builder:visited:toggle")
        await route_builder_toggle_visited(again, state)
        assert (await state.get_data())["exclude_visited"] is False

        await state.set_state(RouteBuilderFlow.waiting_interest)
        stale = FakeCallback(42, "builder:visited:toggle")
        await route_builder_toggle_visited(stale, state)
        assert stale.answers == [("Начните сбор маршрута заново.", True)]
        assert not stale.message.markup_edits

    asyncio.run(scenario())


def test_builder_filters_only_current_users_city_and_keeps_saved_snapshot(tmp_path):
    async def scenario():
        db = str(tmp_path / "places.db")
        await migrate_database(db)
        visited = VisitedRepository(db)
        catalog = get_catalog("perm")
        baseline = build_route(catalog, budget_minutes=240, interest="classic")
        assert baseline is not None
        excluded_slug = baseline.places[0].slug

        await visited.add(42, "perm", excluded_slug)
        if len(baseline.places) > 1:
            await visited.add(77, "perm", baseline.places[1].slug)
            await visited.add(42, "moscow", baseline.places[1].slug)
        expected = build_route(
            catalog,
            budget_minutes=240,
            interest="classic",
            excluded_slugs=(excluded_slug,),
        )
        assert expected is not None

        state = FakeState()
        await state.set_state(RouteBuilderFlow.waiting_interest)
        await state.update_data(budget_minutes=240, exclude_visited=True)
        callback = FakeCallback(42, "builder:interest:classic")
        with patch("app.handlers.main.current_catalog", return_value=catalog):
            await route_builder_interest(callback, state, visited)

        assert callback.answers == [(None, False)]
        text, markup = callback.message.edits[0]
        assert "Посещённые места: исключены" in text
        slugs = tuple(
            parse_place_callback(value)[0]
            for row in markup.inline_keyboard
            for button in row
            if (value := button.callback_data or "").startswith("place:")
        )
        assert slugs == tuple(place.slug for place in expected.places)
        assert excluded_slug not in slugs
        assert await visited.list_place_slugs(42, "perm") == (excluded_slug,)
        assert await state.get_state() is None

        from app.saved_routes import parse_save_callback

        save = next(value for value in callback_values(markup) if value.startswith("savegen:"))
        snapshot = parse_save_callback(save, catalog)
        assert tuple(place.slug for place in snapshot.places) == slugs

    asyncio.run(scenario())


def test_builder_no_new_places_has_clear_empty_state(tmp_path):
    async def scenario():
        db = str(tmp_path / "places.db")
        await migrate_database(db)
        visited = VisitedRepository(db)
        catalog = get_catalog("perm")
        for place in catalog.places:
            await visited.add(42, "perm", place.slug)

        state = FakeState()
        await state.set_state(RouteBuilderFlow.waiting_interest)
        await state.update_data(budget_minutes=240, exclude_visited=True)
        callback = FakeCallback(42, "builder:interest:classic")
        with patch("app.handlers.main.current_catalog", return_value=catalog):
            await route_builder_interest(callback, state, visited)

        assert callback.answers == [(None, False)]
        assert "отключить исключение" in callback.message.edits[0][0]
        assert "menu:home" in callback_values(callback.message.edits[0][1])
        assert await state.get_state() is None

    asyncio.run(scenario())


def test_location_flow_preserves_visit_exclusion_option():
    async def scenario():
        state = FakeState()
        await state.set_state(RouteBuilderFlow.waiting_duration)
        await state.update_data(exclude_visited=True)
        request = FakeCallback(42, "builder:location")
        await route_builder_request_location(request, state)
        assert await state.get_state() == RouteBuilderFlow.waiting_location.state

        message = FakeMessage(location=SimpleNamespace(latitude=55.75, longitude=37.62))
        await route_builder_location(message, state)
        assert await state.get_state() == RouteBuilderFlow.waiting_duration.state
        assert (await state.get_data())["exclude_visited"] is True
        markup = message.answers[-1][1]
        labels = {button.text for row in markup.inline_keyboard for button in row}
        assert "✅ Посещённые исключены" in labels
        assert "✅ Старт: моя геопозиция" in labels

        duration = FakeCallback(42, "builder:duration:240")
        await route_builder_duration(duration, state)
        assert "Посещённые места: исключены" in duration.message.edits[0][0]

    asyncio.run(scenario())

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

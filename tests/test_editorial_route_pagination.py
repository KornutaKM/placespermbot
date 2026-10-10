import asyncio
from types import SimpleNamespace
from unittest.mock import patch

from app.catalog import get_catalog, list_catalogs
from app.handlers.main import editorial_routes_page, menu_routes, route_card
from app.keyboards import route_details_keyboard, routes_keyboard
from app.pagination import PAGE_SIZE, paginate


def callbacks(markup):
    return {
        button.callback_data
        for row in markup.inline_keyboard
        for button in row
        if button.callback_data is not None
    }


class FakeMessage:
    def __init__(self):
        self.edits = []

    async def edit_text(self, text, *, reply_markup=None):
        self.edits.append((text, reply_markup))


class FakeCallback:
    def __init__(self, data):
        self.data = data
        self.from_user = SimpleNamespace(id=42)
        self.message = FakeMessage()
        self.answers = []

    async def answer(self, text=None, *, show_alert=False):
        self.answers.append((text, show_alert))


def test_editorial_route_pages_cover_all_city_routes():
    for city in list_catalogs():
        page_count = paginate(city.routes, 0).total_pages
        collected = []
        for index in range(page_count):
            markup = routes_keyboard(city.routes, city_slug=city.slug, page_index=index)
            values = callbacks(markup)
            visible = [f"route:{route.slug}" for route in paginate(city.routes, index).items]
            assert len(visible) <= PAGE_SIZE
            assert set(visible).issubset(values)
            assert "menu:home" in values
            if page_count > 1:
                assert "noop" in values
            collected.extend(visible)
        assert collected == [f"route:{route.slug}" for route in city.routes]


def test_editorial_route_pages_clamp_indexes():
    city = get_catalog("perm")
    last = paginate(city.routes, 999).index
    assert callbacks(routes_keyboard(city.routes, page_index=999)) == callbacks(
        routes_keyboard(city.routes, page_index=last)
    )
    assert callbacks(routes_keyboard(city.routes, page_index=-1)) == callbacks(
        routes_keyboard(city.routes, page_index=0)
    )
    assert "menu:routes" in callbacks(route_details_keyboard(city.places[:2]))


def test_route_page_callbacks_and_legacy_details():
    async def scenario():
        city = get_catalog("perm")
        last_index = len(city.routes) - 1
        page_index = last_index // PAGE_SIZE
        with patch("app.handlers.main.current_catalog", return_value=city):
            listing = FakeCallback("menu:routes")
            await menu_routes(listing)
            assert "страница 1/" in listing.message.edits[0][0]

            page = FakeCallback(f"routes:page:{page_index}")
            await editorial_routes_page(page)
            route = city.routes[last_index]
            assert f"route:{route.slug}" in callbacks(page.message.edits[0][1])

            details = FakeCallback(f"route:{route.slug}")
            await route_card(details)
            assert f"routes:page:{page_index}" in callbacks(details.message.edits[0][1])

            invalid = FakeCallback("routes:page:-1")
            await editorial_routes_page(invalid)
            assert invalid.answers == [("Некорректная страница.", True)]
            assert not invalid.message.edits

    asyncio.run(scenario())

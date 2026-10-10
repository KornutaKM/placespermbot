import asyncio
from types import SimpleNamespace

from app.catalog_service import CatalogService
from app.database import migrate_database
from app.handlers.main import help_command, help_text, menu_help
from app.keyboards import help_keyboard, home_keyboard
from app.storage import UserCityRepository


class FakeMessage:
    def __init__(self, user_id: int) -> None:
        self.from_user = SimpleNamespace(id=user_id)
        self.answers: list[tuple[str, object]] = []

    async def answer(self, text: str, *, reply_markup=None) -> None:
        self.answers.append((text, reply_markup))


class FakeCallbackMessage:
    def __init__(self) -> None:
        self.edits: list[tuple[str, object]] = []

    async def edit_text(self, text: str, *, reply_markup=None) -> None:
        self.edits.append((text, reply_markup))


class FakeCallback:
    def __init__(self, user_id: int) -> None:
        self.from_user = SimpleNamespace(id=user_id)
        self.message = FakeCallbackMessage()
        self.answered = False

    async def answer(self) -> None:
        self.answered = True


def callbacks(markup) -> set[str]:
    return {
        button.callback_data
        for row in markup.inline_keyboard
        for button in row
        if button.callback_data is not None
    }


def test_help_is_discoverable_from_home_and_explains_supported_actions() -> None:
    assert "menu:help" in callbacks(home_keyboard())
    text = help_text()
    assert "/city" in text
    assert "Собрать маршрут" in text
    assert "Мой гид" in text
    assert "не сохраняется" in text
    assert "ориентировочные" in text


def test_help_keyboard_requires_city_before_exposing_route_actions() -> None:
    assert callbacks(help_keyboard(city_selected=False)) == {"menu:cities"}
    assert callbacks(help_keyboard(city_selected=True)) == {
        "menu:places",
        "builder:start",
        "menu:home",
    }


def test_help_command_before_city_selection_is_read_only(tmp_path) -> None:
    async def scenario() -> None:
        path = str(tmp_path / "places.db")
        await migrate_database(path)
        users = UserCityRepository(path)
        service = CatalogService("saint-petersburg", users)
        message = FakeMessage(42)

        await help_command(message, service)

        assert len(message.answers) == 1
        text, markup = message.answers[0]
        assert "Как пользоваться" in text
        assert callbacks(markup) == {"menu:cities"}
        assert await users.get_city_slug(42) is None

    asyncio.run(scenario())


def test_help_callback_respects_user_city_selection(tmp_path) -> None:
    async def scenario() -> None:
        path = str(tmp_path / "places.db")
        await migrate_database(path)
        users = UserCityRepository(path)
        service = CatalogService("saint-petersburg", users)
        await users.set_city_slug(43, "perm")
        selected = FakeCallback(43)
        first_run = FakeCallback(44)

        await menu_help(selected, service)
        await menu_help(first_run, service)

        assert selected.answered
        assert first_run.answered
        assert callbacks(selected.message.edits[0][1]) == {
            "menu:places",
            "builder:start",
            "menu:home",
        }
        assert callbacks(first_run.message.edits[0][1]) == {"menu:cities"}
        assert await users.get_city_slug(43) == "perm"
        assert await users.get_city_slug(44) is None

    asyncio.run(scenario())

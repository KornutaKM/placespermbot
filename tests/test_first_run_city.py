import asyncio
from types import SimpleNamespace

from app.catalog_service import CatalogService
from app.database import migrate_database
from app.handlers.main import city_command, city_page, start
from app.keyboards import CITY_PAGE_SIZE
from app.storage import UserCityRepository


class FakeState:
    def __init__(self, state: str | None = None) -> None:
        self.state = state
        self.cleared = False

    async def get_state(self) -> str | None:
        return self.state

    async def clear(self) -> None:
        self.state = None
        self.cleared = True


class FakeMessage:
    def __init__(self, user_id: int) -> None:
        self.from_user = SimpleNamespace(id=user_id)
        self.answers: list[tuple[str, object | None]] = []

    async def answer(self, text: str, *, reply_markup=None) -> None:
        self.answers.append((text, reply_markup))


class FakeCallbackMessage:
    def __init__(self) -> None:
        self.edits: list[tuple[str, object | None]] = []

    async def edit_text(self, text: str, *, reply_markup=None) -> None:
        self.edits.append((text, reply_markup))


class FakeCallback:
    def __init__(self, user_id: int, data: str) -> None:
        self.from_user = SimpleNamespace(id=user_id)
        self.data = data
        self.message = FakeCallbackMessage()
        self.answers: list[tuple[str | None, bool]] = []

    async def answer(
        self,
        text: str | None = None,
        *,
        show_alert: bool = False,
    ) -> None:
        self.answers.append((text, show_alert))



def callback_values(markup) -> set[str]:
    return {
        button.callback_data
        for row in markup.inline_keyboard
        for button in row
        if button.callback_data is not None
    }


def button_texts(markup) -> tuple[str, ...]:
    return tuple(
        button.text
        for row in markup.inline_keyboard
        for button in row
    )


def test_first_start_requires_explicit_city_without_persisting_default(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        repository = UserCityRepository(database_path)
        service = CatalogService(
            default_city_slug="saint-petersburg",
            user_city_repo=repository,
        )
        message = FakeMessage(42)
        state = FakeState()

        await start(message, state, service)

        assert state.cleared
        assert await repository.get_city_slug(42) is None
        assert len(message.answers) == 1
        text, markup = message.answers[0]
        assert "Сначала выберите город" in text
        assert callback_values(markup) == {
            *(f"city:set:{catalog.slug}"
              for catalog in service.available_catalogs()[:CITY_PAGE_SIZE]),
            "city:page:1",
            "noop",
        }
        assert "menu:home" not in callback_values(markup)
        assert all(not text.startswith("✅ ") for text in button_texts(markup))

    asyncio.run(scenario())


def test_start_with_saved_city_opens_home_for_that_city(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        repository = UserCityRepository(database_path)
        await repository.set_city_slug(42, "perm")
        service = CatalogService(
            default_city_slug="saint-petersburg",
            user_city_repo=repository,
        )
        message = FakeMessage(42)
        state = FakeState()

        await start(message, state, service)

        assert len(message.answers) == 1
        text, markup = message.answers[0]
        assert "Ваш город: <b>Пермь</b>" in text
        callbacks = callback_values(markup)
        assert "menu:cities" in callbacks
        assert "menu:places" in callbacks

    asyncio.run(scenario())


def test_start_with_stale_city_returns_to_explicit_selection(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        repository = UserCityRepository(database_path)
        await repository.set_city_slug(42, "removed-city")
        service = CatalogService(
            default_city_slug="saint-petersburg",
            user_city_repo=repository,
        )
        message = FakeMessage(42)
        state = FakeState()

        await start(message, state, service)

        text, markup = message.answers[0]
        assert "Сначала выберите город" in text
        assert "menu:home" not in callback_values(markup)
        assert await repository.get_city_slug(42) == "removed-city"

    asyncio.run(scenario())


def test_first_run_can_page_cities_without_selecting_default(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        repository = UserCityRepository(database_path)
        service = CatalogService(
            default_city_slug="saint-petersburg",
            user_city_repo=repository,
        )
        callback = FakeCallback(42, "city:page:1")

        await city_page(callback, service)

        assert callback.answers == [(None, False)]
        assert len(callback.message.edits) == 1
        text, markup = callback.message.edits[0]
        assert "Сначала выберите город" in text
        assert callback_values(markup) == {
            *(f"city:set:{catalog.slug}"
              for catalog in service.available_catalogs()[CITY_PAGE_SIZE:2 * CITY_PAGE_SIZE]),
            "city:page:0",
            "city:page:2",
            "noop",
        }
        assert "menu:home" not in callback_values(markup)
        assert await repository.get_city_slug(42) is None

    asyncio.run(scenario())


def test_invalid_city_page_is_rejected_without_editing(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        service = CatalogService(
            default_city_slug="saint-petersburg",
            user_city_repo=UserCityRepository(database_path),
        )
        callback = FakeCallback(42, "city:page:-1")

        await city_page(callback, service)

        assert not callback.message.edits
        assert callback.answers == [("Страница недоступна.", True)]

    asyncio.run(scenario())


def test_city_command_before_first_selection_keeps_first_run_gate(tmp_path) -> None:
    async def scenario() -> None:
        database_path = str(tmp_path / "places.db")
        await migrate_database(database_path)
        repository = UserCityRepository(database_path)
        service = CatalogService(
            default_city_slug="saint-petersburg",
            user_city_repo=repository,
        )
        message = FakeMessage(42)

        await city_command(message, FakeState(), service)

        text, markup = message.answers[0]
        assert "Сначала выберите город" in text
        assert "menu:home" not in callback_values(markup)
        assert await repository.get_city_slug(42) is None

    asyncio.run(scenario())

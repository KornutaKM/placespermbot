import asyncio
from types import SimpleNamespace

from app.catalog_service import CatalogService
from app.database import migrate_database
from app.handlers.main import start
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
            "city:set:perm",
            "city:set:saint-petersburg",
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

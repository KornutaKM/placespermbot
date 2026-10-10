import asyncio
from types import SimpleNamespace
from unittest.mock import patch

from app.catalog import get_catalog
from app.database import migrate_database
from app.handlers.main import (
    complete_saved_route_callback,
    delete_saved_route,
    request_saved_route_deletion,
    saved_route_card,
)
from app.keyboards import (
    saved_route_delete_confirmation_keyboard,
    saved_route_details_keyboard,
)
from app.storage import CompletedRoutesRepository, SavedRoutesRepository, VisitedRepository

CITY = "perm"


class FakeMessage:
    def __init__(self) -> None:
        self.text_edits: list[tuple[str, object]] = []
        self.markup_edits: list[object] = []

    async def edit_text(self, text: str, *, reply_markup=None) -> None:
        self.text_edits.append((text, reply_markup))

    async def edit_reply_markup(self, *, reply_markup=None) -> None:
        self.markup_edits.append(reply_markup)


class FakeCallback:
    def __init__(self, user_id: int, data: str) -> None:
        self.from_user = SimpleNamespace(id=user_id)
        self.data = data
        self.message = FakeMessage()
        self.answers: list[tuple[str | None, bool]] = []

    async def answer(self, text: str | None = None, *, show_alert: bool = False) -> None:
        self.answers.append((text, show_alert))


def callbacks(markup) -> set[str]:
    return {
        button.callback_data
        for row in markup.inline_keyboard
        for button in row
        if button.callback_data is not None
    }


def test_delete_confirmation_keyboard_has_explicit_confirm_and_cancel() -> None:
    catalog = get_catalog(CITY)
    place = catalog.places[0]
    route_id = "abcdef0123456789"
    confirm = callbacks(saved_route_delete_confirmation_keyboard(route_id))
    assert confirm == {
        "savedroute:delete-confirm:abcdef0123456789",
        "savedroute:abcdef0123456789",
    }
    assert all(len(value.encode("utf-8")) <= 64 for value in confirm)

    from app.saved_routes import SavedRoute

    route = SavedRoute(
        route_id=route_id,
        city_slug=CITY,
        interest="classic",
        budget_minutes=120,
        place_slugs=(place.slug,),
        created_at="2026-10-10 12:00:00",
    )
    normal = callbacks(saved_route_details_keyboard(route, (place,)))
    assert f"savedroute:delete:{route_id}" in normal
    assert f"savedroute:delete-confirm:{route_id}" not in normal


def test_saved_route_deletion_needs_second_click_and_cancel_is_read_only(tmp_path) -> None:
    async def scenario() -> None:
        path = str(tmp_path / "places.db")
        await migrate_database(path)
        saved = SavedRoutesRepository(path)
        completed = CompletedRoutesRepository(path)
        catalog = get_catalog(CITY)
        place = catalog.places[0]
        route = await saved.save(42, CITY, "classic", 120, (place.slug,))

        with patch("app.handlers.main.current_catalog", return_value=catalog):
            request = FakeCallback(42, f"savedroute:delete:{route.route_id}")
            await request_saved_route_deletion(request, saved)
            assert request.answers == [(None, False)]
            assert "Удалить сохранённый маршрут" in request.message.text_edits[0][0]
            assert callbacks(request.message.text_edits[0][1]) == {
                f"savedroute:delete-confirm:{route.route_id}",
                f"savedroute:{route.route_id}",
            }
            assert await saved.get(42, CITY, route.route_id) is not None

            # The cancel button goes back to the original route card.
            cancel = FakeCallback(42, f"savedroute:{route.route_id}")
            await saved_route_card(cancel, saved, completed)
            assert cancel.message.text_edits
            assert f"savedroute:delete:{route.route_id}" in callbacks(
                cancel.message.text_edits[0][1]
            )
            assert await saved.get(42, CITY, route.route_id) is not None

            confirm = FakeCallback(42, f"savedroute:delete-confirm:{route.route_id}")
            await delete_saved_route(confirm, saved, completed)
            assert await saved.get(42, CITY, route.route_id) is None
            assert "Здесь пока пусто" in confirm.message.text_edits[0][0]

    asyncio.run(scenario())


def test_deleted_route_confirmation_is_scoped_to_user_and_city(tmp_path) -> None:
    async def scenario() -> None:
        path = str(tmp_path / "places.db")
        await migrate_database(path)
        saved = SavedRoutesRepository(path)
        completed = CompletedRoutesRepository(path)
        catalog = get_catalog(CITY)
        route = await saved.save(
            42, CITY, "classic", 120, (catalog.places[0].slug,)
        )

        with patch("app.handlers.main.current_catalog", return_value=catalog):
            outsider = FakeCallback(43, f"savedroute:delete-confirm:{route.route_id}")
            await delete_saved_route(outsider, saved, completed)
            assert outsider.answers == [("Сохранённый маршрут не найден.", True)]
            assert not outsider.message.text_edits
            assert await saved.get(42, CITY, route.route_id) is not None

        with patch(
            "app.handlers.main.current_catalog", return_value=get_catalog("moscow")
        ):
            wrong_city = FakeCallback(42, f"savedroute:delete:{route.route_id}")
            await request_saved_route_deletion(wrong_city, saved)
            assert wrong_city.answers == [("Сохранённый маршрут не найден.", True)]
            assert not wrong_city.message.text_edits
            assert await saved.get(42, CITY, route.route_id) is not None

    asyncio.run(scenario())


def test_completion_refreshes_saved_route_keyboard_and_keeps_history(tmp_path) -> None:
    async def scenario() -> None:
        path = str(tmp_path / "places.db")
        await migrate_database(path)
        saved = SavedRoutesRepository(path)
        completed = CompletedRoutesRepository(path)
        visited = VisitedRepository(path)
        catalog = get_catalog(CITY)
        places = catalog.places[:2]
        route = await saved.save(
            42, CITY, "classic", 120, tuple(place.slug for place in places)
        )

        with patch("app.handlers.main.current_catalog", return_value=catalog):
            mark = FakeCallback(42, f"savedroute:complete:{route.route_id}")
            await complete_saved_route_callback(mark, saved, visited, completed)
            assert len(mark.message.markup_edits) == 1
            assert f"completedroute:{route.route_id}" in callbacks(
                mark.message.markup_edits[0]
            )
            assert f"savedroute:complete:{route.route_id}" not in callbacks(
                mark.message.markup_edits[0]
            )
            assert await completed.contains(42, CITY, route.route_id)

            repeat = FakeCallback(42, f"savedroute:complete:{route.route_id}")
            await complete_saved_route_callback(repeat, saved, visited, completed)
            assert repeat.answers == [
                ("Этот маршрут уже отмечен как пройденный.", True)
            ]
            assert not repeat.message.markup_edits

            confirm = FakeCallback(42, f"savedroute:delete-confirm:{route.route_id}")
            await delete_saved_route(confirm, saved, completed)
            assert await saved.get(42, CITY, route.route_id) is None
            assert await completed.contains(42, CITY, route.route_id)
            snapshot = await completed.get_snapshot(42, CITY, route.route_id)
            assert snapshot is not None
            assert snapshot.place_slugs == tuple(place.slug for place in places)

    asyncio.run(scenario())


def test_invalid_and_stale_delete_callbacks_fail_closed(tmp_path) -> None:
    async def scenario() -> None:
        path = str(tmp_path / "places.db")
        await migrate_database(path)
        saved = SavedRoutesRepository(path)
        completed = CompletedRoutesRepository(path)

        with patch("app.handlers.main.current_catalog", return_value=get_catalog(CITY)):
            for action in ("savedroute:delete:", "savedroute:delete-confirm:"):
                callback = FakeCallback(42, action)
                if action.endswith("confirm:"):
                    await delete_saved_route(callback, saved, completed)
                else:
                    await request_saved_route_deletion(callback, saved)
                assert callback.answers == [("Некорректный маршрут.", True)]
                assert not callback.message.text_edits

    asyncio.run(scenario())

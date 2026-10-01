from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, CallbackQuery, Message, ReplyKeyboardRemove

from app.catalog import CityCatalog
from app.catalog_context import get_current_catalog
from app.catalog_service import CatalogService
from app.config import get_settings
from app.events import get_event_providers
from app.excursions import get_excursion_providers
from app.keyboards import (
    back_home_keyboard,
    categories_keyboard,
    cities_keyboard,
    completed_route_details_keyboard,
    completed_routes_keyboard,
    data_controls_keyboard,
    data_delete_confirm_keyboard,
    event_providers_keyboard,
    excursion_providers_keyboard,
    generated_route_keyboard,
    home_keyboard,
    interests_keyboard,
    paginated_places_keyboard,
    personal_route_duration_keyboard,
    personalized_places_keyboard,
    place_keyboard,
    place_route_duration_keyboard,
    places_keyboard,
    profile_keyboard,
    request_location_keyboard,
    route_details_keyboard,
    route_duration_keyboard,
    route_interest_keyboard,
    routes_keyboard,
    saved_route_details_keyboard,
    saved_routes_keyboard,
    visited_places_keyboard,
)
from app.navigation import (
    category_context,
    dismissed_context,
    favorites_context,
    home_context,
    nearby_child_context,
    parse_dismissed_callback,
    parse_favorite_callback,
    parse_nearby_callback,
    parse_place_callback,
    parse_place_route_callback,
    parse_place_route_duration_callback,
    parse_similar_callback,
    parse_visited_callback,
    place_callback,
    place_route_callback,
    search_context,
    similar_child_context,
)
from app.pagination import Page, paginate
from app.personal_route import build_personal_route
from app.place_route import build_place_route
from app.planner import INTEREST_LABELS, build_route
from app.profile import ProfileSummary, build_profile_summary, profile_text
from app.recommendations import recommend_personalized
from app.route_completion import complete_saved_route
from app.saved_routes import (
    PERSONAL_ROUTE_INTEREST,
    PERSONAL_ROUTE_LABEL,
    PLACE_ROUTE_INTEREST,
    PLACE_ROUTE_LABEL,
    build_save_callback,
    parse_save_callback,
    route_interest_label,
)
from app.search_ui import search_not_found_text, search_prompt, search_results_text
from app.similarity import find_similar_places
from app.storage import (
    CompletedRoutesRepository,
    DismissedRepository,
    FavoritesRepository,
    InterestsRepository,
    SavedRoutesRepository,
    VisitedRepository,
)
from app.user_data_controls import (
    UserDataControlsRepository,
    bound_city_slug,
)
from app.user_export import (
    build_user_export,
    export_filename,
    serialize_user_export,
)

router = Router()


class SearchFlow(StatesGroup):
    waiting_query = State()


class RouteBuilderFlow(StatesGroup):
    waiting_location = State()
    waiting_duration = State()
    waiting_interest = State()


class NearbyFlow(StatesGroup):
    waiting_location = State()


class PersonalRouteFlow(StatesGroup):
    waiting_location = State()
    waiting_duration = State()


LOCATION_REQUEST_STATES = {
    RouteBuilderFlow.waiting_location.state,
    NearbyFlow.waiting_location.state,
    PersonalRouteFlow.waiting_location.state,
}


def current_catalog() -> CityCatalog:
    return get_current_catalog()


def home_text(catalog: CityCatalog) -> str:
    return (
        f"📍 <b>{catalog.name}</b>\n\n"
        "Что хотите сделать?\n\n"
        "Можно выбрать места, готовую прогулку или собрать маршрут под себя."
    )


@router.message(CommandStart())
async def start(
    message: Message,
    state: FSMContext,
    catalog_service: CatalogService,
) -> None:
    previous_state = await state.get_state()
    await state.clear()
    if previous_state in LOCATION_REQUEST_STATES:
        await message.answer(
            "Запрос геопозиции отменён.",
            reply_markup=ReplyKeyboardRemove(),
        )

    selected = await catalog_service.selected_for_user(message.from_user.id)
    if selected is None:
        await message.answer(
            "👋 <b>Добро пожаловать!</b>\n\n"
            "Я — городской гид в Telegram. Сначала выберите город — "
            "я сохраню этот выбор, и его всегда можно будет изменить через /city.",
            reply_markup=cities_keyboard(
                catalog_service.available_catalogs(),
                None,
                include_home=False,
            ),
        )
        return

    await message.answer(
        "👋 <b>Добро пожаловать!</b>\n\n"
        f"Ваш город: <b>{selected.name}</b>.\n\n"
        + home_text(selected),
        reply_markup=home_keyboard(),
    )


@router.callback_query(F.data == "menu:home")
async def menu_home(callback: CallbackQuery, state: FSMContext) -> None:
    previous_state = await state.get_state()
    await state.clear()
    if previous_state in LOCATION_REQUEST_STATES:
        await callback.message.answer(
            "Запрос геопозиции отменён.",
            reply_markup=ReplyKeyboardRemove(),
        )
    catalog = current_catalog()
    await callback.message.edit_text(home_text(catalog), reply_markup=home_keyboard())
    await callback.answer()


async def build_current_profile(
    user_id: int,
    dismissed_repo: DismissedRepository,
    favorites_repo: FavoritesRepository,
    interests_repo: InterestsRepository,
    visited_repo: VisitedRepository,
    saved_routes_repo: SavedRoutesRepository,
    completed_routes_repo: CompletedRoutesRepository,
) -> ProfileSummary:
    return await build_profile_summary(
        user_id,
        current_catalog(),
        dismissed_repo=dismissed_repo,
        favorites_repo=favorites_repo,
        interests_repo=interests_repo,
        visited_repo=visited_repo,
        saved_routes_repo=saved_routes_repo,
        completed_routes_repo=completed_routes_repo,
    )


@router.message(Command("profile"))
async def profile_command(
    message: Message,
    dismissed_repo: DismissedRepository,
    favorites_repo: FavoritesRepository,
    interests_repo: InterestsRepository,
    visited_repo: VisitedRepository,
    saved_routes_repo: SavedRoutesRepository,
    completed_routes_repo: CompletedRoutesRepository,
) -> None:
    summary = await build_current_profile(
        message.from_user.id,
        dismissed_repo,
        favorites_repo,
        interests_repo,
        visited_repo,
        saved_routes_repo,
        completed_routes_repo,
    )
    await message.answer(
        profile_text(summary),
        reply_markup=profile_keyboard(),
    )


@router.callback_query(F.data == "menu:profile")
async def menu_profile(
    callback: CallbackQuery,
    dismissed_repo: DismissedRepository,
    favorites_repo: FavoritesRepository,
    interests_repo: InterestsRepository,
    visited_repo: VisitedRepository,
    saved_routes_repo: SavedRoutesRepository,
    completed_routes_repo: CompletedRoutesRepository,
) -> None:
    summary = await build_current_profile(
        callback.from_user.id,
        dismissed_repo,
        favorites_repo,
        interests_repo,
        visited_repo,
        saved_routes_repo,
        completed_routes_repo,
    )
    await callback.message.edit_text(
        profile_text(summary),
        reply_markup=profile_keyboard(),
    )
    await callback.answer()


async def send_user_export(
    message: Message,
    user_id: int,
    dismissed_repo: DismissedRepository,
    favorites_repo: FavoritesRepository,
    interests_repo: InterestsRepository,
    visited_repo: VisitedRepository,
    saved_routes_repo: SavedRoutesRepository,
    completed_routes_repo: CompletedRoutesRepository,
) -> None:
    catalog = current_catalog()
    data = await build_user_export(
        user_id,
        catalog,
        dismissed_repo=dismissed_repo,
        favorites_repo=favorites_repo,
        interests_repo=interests_repo,
        visited_repo=visited_repo,
        saved_routes_repo=saved_routes_repo,
        completed_routes_repo=completed_routes_repo,
    )
    document = BufferedInputFile(
        serialize_user_export(data),
        filename=export_filename(catalog),
    )
    await message.answer_document(
        document,
        caption=(
            f"📦 Экспорт данных · {catalog.name}\n\n"
            "Файл содержит только ваши явные данные в активном городе. "
            "Геопозиция и история просмотров не экспортируются."
        ),
    )


@router.message(Command("export"))
async def export_command(
    message: Message,
    dismissed_repo: DismissedRepository,
    favorites_repo: FavoritesRepository,
    interests_repo: InterestsRepository,
    visited_repo: VisitedRepository,
    saved_routes_repo: SavedRoutesRepository,
    completed_routes_repo: CompletedRoutesRepository,
) -> None:
    await send_user_export(
        message,
        message.from_user.id,
        dismissed_repo,
        favorites_repo,
        interests_repo,
        visited_repo,
        saved_routes_repo,
        completed_routes_repo,
    )


@router.callback_query(F.data == "profile:export")
async def export_from_profile(
    callback: CallbackQuery,
    dismissed_repo: DismissedRepository,
    favorites_repo: FavoritesRepository,
    interests_repo: InterestsRepository,
    visited_repo: VisitedRepository,
    saved_routes_repo: SavedRoutesRepository,
    completed_routes_repo: CompletedRoutesRepository,
) -> None:
    await send_user_export(
        callback.message,
        callback.from_user.id,
        dismissed_repo,
        favorites_repo,
        interests_repo,
        visited_repo,
        saved_routes_repo,
        completed_routes_repo,
    )
    await callback.answer("Экспорт подготовлен")


@router.callback_query(F.data == "profile:data")
async def data_controls(callback: CallbackQuery) -> None:
    catalog = current_catalog()
    await callback.message.edit_text(
        "🧹 <b>Управление данными</b>\n\n"
        f"Активный город: <b>{catalog.name}</b>.\n\n"
        "Можно сначала выгрузить JSON-экспорт, а затем удалить "
        "ваши интересы, избранное, посещённые места, скрытые рекомендации, "
        "сохранённые и пройденные маршруты "
        "в этом городе. Выбор активного города останется сохранён.",
        reply_markup=data_controls_keyboard(catalog.slug),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("profile:data:confirm:"))
async def data_delete_confirm(callback: CallbackQuery) -> None:
    catalog = current_catalog()
    try:
        city_slug = bound_city_slug(
            callback.data,
            prefix="profile:data:confirm:",
            current_city_slug=catalog.slug,
        )
    except ValueError:
        await callback.answer(
            "Активный город изменился. Откройте управление данными заново.",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "⚠️ <b>Подтвердите удаление</b>\n\n"
        f"Город: <b>{catalog.name}</b>.\n\n"
        "Будут безвозвратно удалены ваши интересы, избранное, "
        "посещённые места, скрытые рекомендации, сохранённые "
        "и пройденные маршруты этого города.\n\n"
        "Сам каталог и выбор активного города не удаляются.",
        reply_markup=data_delete_confirm_keyboard(city_slug),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("profile:data:delete:"))
async def delete_city_user_data(
    callback: CallbackQuery,
    data_controls_repo: UserDataControlsRepository,
) -> None:
    catalog = current_catalog()
    try:
        city_slug = bound_city_slug(
            callback.data,
            prefix="profile:data:delete:",
            current_city_slug=catalog.slug,
        )
    except ValueError:
        await callback.answer(
            "Активный город изменился. Удаление отменено.",
            show_alert=True,
        )
        return

    result = await data_controls_repo.delete_city_data(
        callback.from_user.id,
        city_slug,
    )
    await callback.message.edit_text(
        "🧹 <b>Данные удалены</b>\n\n"
        f"Город: <b>{catalog.name}</b>\n"
        f"🎯 Интересы: {result.interests}\n"
        f"❤️ Избранное: {result.favorites}\n"
        f"✅ Посещённые: {result.visited}\n"
        f"🙈 Не интересно: {result.dismissed}\n"
        f"🧭 Сохранённые маршруты: {result.saved_routes}\n"
        f"🏁 Пройденные маршруты: {result.completed_routes}\n"
        f"📸 Snapshots маршрутов: {result.completed_route_snapshots}\n\n"
        f"Всего удалено записей: <b>{result.total}</b>.\n"
        "Активный город остался выбран.",
        reply_markup=profile_keyboard(),
    )
    await callback.answer("Данные удалены")


@router.message(Command("city"))
async def city_command(
    message: Message,
    state: FSMContext,
    catalog_service: CatalogService,
) -> None:
    previous_state = await state.get_state()
    await state.clear()
    if previous_state in LOCATION_REQUEST_STATES:
        await message.answer(
            "Запрос геопозиции отменён.",
            reply_markup=ReplyKeyboardRemove(),
        )

    catalog = current_catalog()
    await message.answer(
        "🌆 <b>Выбор города</b>\n\n"
        f"Сейчас выбран: <b>{catalog.name}</b>.\n"
        "Выберите город из доступных каталогов:",
        reply_markup=cities_keyboard(
            catalog_service.available_catalogs(),
            catalog.slug,
        ),
    )


@router.callback_query(F.data == "menu:cities")
async def menu_cities(
    callback: CallbackQuery,
    catalog_service: CatalogService,
) -> None:
    catalog = current_catalog()
    await callback.message.edit_text(
        "🌆 <b>Выбор города</b>\n\n"
        f"Сейчас выбран: <b>{catalog.name}</b>.\n"
        "Выберите город из доступных каталогов:",
        reply_markup=cities_keyboard(
            catalog_service.available_catalogs(),
            catalog.slug,
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("city:set:"))
async def set_city(
    callback: CallbackQuery,
    state: FSMContext,
    catalog_service: CatalogService,
) -> None:
    previous_state = await state.get_state()
    city_slug = callback.data.removeprefix("city:set:").strip()
    try:
        catalog = await catalog_service.set_for_user(
            callback.from_user.id,
            city_slug,
        )
    except RuntimeError:
        await callback.answer("Этот город недоступен.", show_alert=True)
        return

    await state.clear()
    if previous_state in LOCATION_REQUEST_STATES:
        await callback.message.answer(
            "Запрос геопозиции отменён.",
            reply_markup=ReplyKeyboardRemove(),
        )
    await callback.message.edit_text(
        home_text(catalog),
        reply_markup=home_keyboard(),
    )
    await callback.answer(f"Город: {catalog.name}")


@router.callback_query(F.data == "menu:places")
async def menu_places(callback: CallbackQuery) -> None:
    catalog = current_catalog()
    await callback.message.edit_text(
        "📍 <b>Куда сходить</b>\n\nВыберите тип места:",
        reply_markup=categories_keyboard(catalog.category_labels),
    )
    await callback.answer()


async def show_category_page(
    callback: CallbackQuery,
    category_key: str,
    page_index: int,
) -> None:
    catalog = current_catalog()
    places = catalog.places_for_category(category_key)
    label = catalog.category_labels.get(category_key)

    if label is None or not places:
        await callback.answer("Для этой подборки пока нет мест.", show_alert=True)
        return

    page = paginate(places, page_index)
    await callback.message.edit_text(
        f"<b>{label}</b>\n\n"
        f"Мест: {page.total_items} · страница {page.number}/{page.total_pages}\n\n"
        "Выберите место. Динамические цены и расписания не фиксируются "
        "как статические данные.",
        reply_markup=paginated_places_keyboard(
            page,
            page_callback_prefix=f"catpage:{category_key}",
            back_callback="menu:places",
            back_text="← Категории",
            place_context=category_context(category_key, page.index),
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cat:"))
async def category(callback: CallbackQuery) -> None:
    category_key = callback.data.split(":", 1)[1]
    await show_category_page(callback, category_key, 0)


@router.callback_query(F.data.startswith("catpage:"))
async def category_page(callback: CallbackQuery) -> None:
    try:
        _, category_key, raw_page = callback.data.split(":", 2)
        page_index = int(raw_page)
    except (ValueError, AttributeError):
        await callback.answer("Некорректная страница.", show_alert=True)
        return

    await show_category_page(callback, category_key, page_index)


@router.callback_query(F.data.startswith("place:"))
async def place_card(
    callback: CallbackQuery,
    dismissed_repo: DismissedRepository,
    favorites_repo: FavoritesRepository,
    visited_repo: VisitedRepository,
) -> None:
    catalog = current_catalog()
    try:
        slug, context = parse_place_callback(callback.data)
    except ValueError:
        await callback.answer("Некорректная карточка места.", show_alert=True)
        return

    place = catalog.place_by_slug(slug)
    if place is None:
        await callback.answer("Место не найдено.", show_alert=True)
        return

    access = "💸 Бесплатное пространство" if place.is_free else "🎟 Условия посещения уточняются"
    tags = " · ".join(f"#{tag.replace(' ', '_')}" for tag in place.tags)
    is_dismissed = await dismissed_repo.contains(
        callback.from_user.id,
        catalog.slug,
        place.slug,
    )
    is_favorite = await favorites_repo.contains(
        callback.from_user.id,
        catalog.slug,
        place.slug,
    )
    is_visited = await visited_repo.contains(
        callback.from_user.id,
        catalog.slug,
        place.slug,
    )

    await callback.message.edit_text(
        f"{place.emoji} <b>{place.title}</b>\n\n"
        f"{place.summary}\n\n"
        f"📍 {place.district}\n"
        f"⏱ Ориентир на посещение: ~{place.visit_minutes} мин\n"
        f"{access}\n\n"
        f"{tags}\n\n"
        f"🔎 Источник: <a href=\"{place.source.url}\">{place.source.name}</a>\n"
        f"Проверено: {place.source.checked_at.strftime('%d.%m.%Y')}",
        reply_markup=place_keyboard(
            place,
            is_dismissed=is_dismissed,
            is_favorite=is_favorite,
            is_visited=is_visited,
            context=context,
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("proute:"))
async def place_route_start(callback: CallbackQuery) -> None:
    catalog = current_catalog()
    try:
        origin_slug, parent_context = parse_place_route_callback(callback.data)
    except ValueError:
        await callback.answer(
            "Не удалось открыть конструктор маршрута.",
            show_alert=True,
        )
        return

    origin = catalog.place_by_slug(origin_slug)
    if origin is None:
        await callback.answer("Исходное место не найдено.", show_alert=True)
        return

    await callback.message.edit_text(
        "🪄 <b>Маршрут отсюда</b>\n\n"
        f"Старт: <b>{origin.title}</b>.\n"
        "Выберите доступное время. Первая точка останется выбранным местом, "
        "затем маршрут дополнится похожими и ближайшими точками.",
        reply_markup=place_route_duration_keyboard(
            origin.slug,
            parent_context,
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("prouted:"))
async def place_route_duration(callback: CallbackQuery) -> None:
    catalog = current_catalog()
    try:
        (
            budget_minutes,
            origin_slug,
            parent_context,
        ) = parse_place_route_duration_callback(callback.data)
    except ValueError:
        await callback.answer(
            "Не удалось прочитать параметры маршрута.",
            show_alert=True,
        )
        return

    origin = catalog.place_by_slug(origin_slug)
    if origin is None:
        await callback.answer("Исходное место не найдено.", show_alert=True)
        return

    route = build_place_route(
        catalog,
        origin.slug,
        budget_minutes=budget_minutes,
    )
    if route is None or not route.places:
        await callback.message.edit_text(
            "Не удалось собрать маршрут под этот бюджет времени. "
            "Попробуйте выбрать больше времени.",
            reply_markup=place_route_duration_keyboard(
                origin.slug,
                parent_context,
            ),
        )
        await callback.answer()
        return

    stops = "\n".join(
        f"{index}. {place.emoji} {place.title} — ~{place.visit_minutes} мин"
        for index, place in enumerate(route.places, start=1)
    )
    hours, minutes = divmod(route.estimated_minutes, 60)

    await callback.message.edit_text(
        f"🪄 <b>{PLACE_ROUTE_LABEL}</b>\n\n"
        f"Старт: <b>{origin.title}</b>\n"
        f"Бюджет: {route.budget_minutes // 60} ч\n"
        f"Оценка маршрута: ~{hours} ч {minutes:02d} мин\n"
        f"Пешком между точками: ~{route.distance_km:g} км\n"
        f"Точек: {len(route.places)}\n\n"
        f"<b>Маршрут:</b>\n{stops}",
        reply_markup=generated_route_keyboard(
            route.places,
            save_callback=build_save_callback(catalog, route),
            restart_callback=place_route_callback(
                origin.slug,
                parent_context,
            ),
            restart_text="🪄 Другой бюджет",
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("similar:"))
async def similar_places(callback: CallbackQuery) -> None:
    catalog = current_catalog()
    try:
        origin_slug, parent_context = parse_similar_callback(callback.data)
    except ValueError:
        await callback.answer(
            "Не удалось открыть похожие места.",
            show_alert=True,
        )
        return

    origin = catalog.place_by_slug(origin_slug)
    if origin is None:
        await callback.answer("Исходное место не найдено.", show_alert=True)
        return

    results = find_similar_places(catalog, origin.slug, limit=5)
    back_callback = place_callback(origin.slug, parent_context)

    if not results:
        await callback.message.edit_text(
            f"🔗 <b>Похожие на {origin.title}</b>\n\n"
            "В текущем каталоге пока нет достаточно похожих мест.",
            reply_markup=places_keyboard(
                (),
                back_callback=back_callback,
                back_text="← К исходному месту",
            ),
        )
        await callback.answer()
        return

    lines = "\n".join(
        f"{index}. {item.place.emoji} <b>{item.place.title}</b>\n"
        f"   ↳ {' · '.join(item.reasons)}"
        for index, item in enumerate(results, start=1)
    )
    places = tuple(item.place for item in results)
    await callback.message.edit_text(
        f"🔗 <b>Похожие на {origin.title}</b>\n\n"
        f"{lines}",
        reply_markup=places_keyboard(
            places,
            back_callback=back_callback,
            back_text="← К исходному месту",
            place_context=similar_child_context(
                origin.slug,
                parent_context,
            ),
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("favorite:"))
async def favorite_action(
    callback: CallbackQuery,
    dismissed_repo: DismissedRepository,
    favorites_repo: FavoritesRepository,
    visited_repo: VisitedRepository,
) -> None:
    catalog = current_catalog()
    try:
        action, slug, context = parse_favorite_callback(callback.data)
    except ValueError:
        await callback.answer("Не удалось изменить избранное.", show_alert=True)
        return

    place = catalog.place_by_slug(slug)

    if place is None:
        await callback.answer("Не удалось изменить избранное.", show_alert=True)
        return

    if action == "add":
        await favorites_repo.add(callback.from_user.id, catalog.slug, place.slug)
        is_favorite = True
        message = "Добавлено в избранное"
    else:
        await favorites_repo.remove(callback.from_user.id, catalog.slug, place.slug)
        is_favorite = False
        message = "Удалено из избранного"

    is_dismissed = await dismissed_repo.contains(
        callback.from_user.id,
        catalog.slug,
        place.slug,
    )
    is_visited = await visited_repo.contains(
        callback.from_user.id,
        catalog.slug,
        place.slug,
    )
    await callback.message.edit_reply_markup(
        reply_markup=place_keyboard(
            place,
            is_dismissed=is_dismissed,
            is_favorite=is_favorite,
            is_visited=is_visited,
            context=context,
        )
    )
    await callback.answer(message)


@router.callback_query(F.data.startswith("visit:"))
async def visited_action(
    callback: CallbackQuery,
    dismissed_repo: DismissedRepository,
    favorites_repo: FavoritesRepository,
    visited_repo: VisitedRepository,
) -> None:
    catalog = current_catalog()
    try:
        action, slug, context = parse_visited_callback(callback.data)
    except ValueError:
        await callback.answer("Не удалось изменить историю.", show_alert=True)
        return

    place = catalog.place_by_slug(slug)
    if place is None:
        await callback.answer("Место не найдено.", show_alert=True)
        return

    if action == "add":
        await visited_repo.add(callback.from_user.id, catalog.slug, place.slug)
        is_visited = True
        message = "Отмечено как посещённое"
    else:
        await visited_repo.remove(callback.from_user.id, catalog.slug, place.slug)
        is_visited = False
        message = "Отметка посещения снята"

    is_dismissed = await dismissed_repo.contains(
        callback.from_user.id,
        catalog.slug,
        place.slug,
    )
    is_favorite = await favorites_repo.contains(
        callback.from_user.id,
        catalog.slug,
        place.slug,
    )
    await callback.message.edit_reply_markup(
        reply_markup=place_keyboard(
            place,
            is_dismissed=is_dismissed,
            is_favorite=is_favorite,
            is_visited=is_visited,
            context=context,
        )
    )
    await callback.answer(message)


@router.callback_query(F.data.startswith("dismiss:"))
async def dismissed_action(
    callback: CallbackQuery,
    dismissed_repo: DismissedRepository,
    favorites_repo: FavoritesRepository,
    visited_repo: VisitedRepository,
) -> None:
    catalog = current_catalog()
    try:
        action, slug, context = parse_dismissed_callback(callback.data)
    except ValueError:
        await callback.answer(
            "Не удалось изменить персональные рекомендации.",
            show_alert=True,
        )
        return

    place = catalog.place_by_slug(slug)
    if place is None:
        await callback.answer("Место не найдено.", show_alert=True)
        return

    if action == "add":
        await dismissed_repo.add(callback.from_user.id, catalog.slug, place.slug)
        is_dismissed = True
        message = "Скрыто из «Для меня»"
    else:
        await dismissed_repo.remove(callback.from_user.id, catalog.slug, place.slug)
        is_dismissed = False
        message = "Возвращено в рекомендации"

    is_favorite = await favorites_repo.contains(
        callback.from_user.id,
        catalog.slug,
        place.slug,
    )
    is_visited = await visited_repo.contains(
        callback.from_user.id,
        catalog.slug,
        place.slug,
    )
    await callback.message.edit_reply_markup(
        reply_markup=place_keyboard(
            place,
            is_dismissed=is_dismissed,
            is_favorite=is_favorite,
            is_visited=is_visited,
            context=context,
        )
    )
    await callback.answer(message)


@router.callback_query(F.data.startswith("geo:"))
async def place_location(callback: CallbackQuery) -> None:
    catalog = current_catalog()
    slug = callback.data.split(":", 1)[1]
    place = catalog.place_by_slug(slug)
    if place is None:
        await callback.answer("Место не найдено.", show_alert=True)
        return

    await callback.message.answer_location(
        latitude=place.latitude,
        longitude=place.longitude,
    )
    await callback.answer("Геопозиция отправлена")


@router.callback_query(F.data.startswith("nearby:"))
async def nearby(callback: CallbackQuery) -> None:
    catalog = current_catalog()
    try:
        slug, context = parse_nearby_callback(callback.data)
    except ValueError:
        await callback.answer("Некорректный запрос ближайших мест.", show_alert=True)
        return

    origin = catalog.place_by_slug(slug)
    if origin is None:
        await callback.answer("Место не найдено.", show_alert=True)
        return

    nearby_items = catalog.nearby_places(slug)
    if not nearby_items:
        await callback.answer("Рядом пока нет точек из нашего каталога.", show_alert=True)
        return

    lines = [
        f"{index}. {place.emoji} {place.title} — ~{distance:.1f} км"
        for index, (place, distance) in enumerate(nearby_items, start=1)
    ]
    places = tuple(place for place, _ in nearby_items)

    await callback.message.edit_text(
        f"✨ <b>Что рядом с «{origin.title}»</b>\n\n" + "\n".join(lines),
        reply_markup=places_keyboard(
            places,
            back_callback=place_callback(origin.slug, context),
            back_text=f"← {origin.title}",
            place_context=nearby_child_context(origin.slug, context),
        ),
    )
    await callback.answer()


async def show_personal_page(
    callback: CallbackQuery,
    dismissed_repo: DismissedRepository,
    favorites_repo: FavoritesRepository,
    interests_repo: InterestsRepository,
    visited_repo: VisitedRepository,
    completed_routes_repo: CompletedRoutesRepository,
    page_index: int,
) -> None:
    catalog = current_catalog()
    interests = await interests_repo.list_interests(
        callback.from_user.id,
        catalog.slug,
    )

    if not interests:
        await callback.message.edit_text(
            "🎯 <b>Для меня</b>\n\n"
            "Выберите интересы. Я сохраню только те варианты, которые вы отметите сами.",
            reply_markup=interests_keyboard(()),
        )
        await callback.answer()
        return

    dismissed_slugs = await dismissed_repo.list_place_slugs(
        callback.from_user.id,
        catalog.slug,
    )
    favorite_slugs = await favorites_repo.list_place_slugs(
        callback.from_user.id,
        catalog.slug,
    )
    visited_slugs = await visited_repo.list_place_slugs(
        callback.from_user.id,
        catalog.slug,
    )
    completed_snapshots = await completed_routes_repo.list_snapshots(
        callback.from_user.id,
        catalog.slug,
    )
    completed_route_place_slugs = {
        slug
        for snapshot in completed_snapshots
        for slug in snapshot.place_slugs
    }
    recommendations = recommend_personalized(
        catalog,
        interests,
        limit=len(catalog.places),
        favorite_slugs=favorite_slugs,
        visited_slugs=visited_slugs,
        completed_route_place_slugs=completed_route_place_slugs,
        exclude_slugs=(
            set(visited_slugs)
            | set(dismissed_slugs)
            | completed_route_place_slugs
        ),
    )
    page = paginate(recommendations, page_index)
    place_page = Page(
        items=tuple(item.place for item in page.items),
        index=page.index,
        total_pages=page.total_pages,
        total_items=page.total_items,
    )
    labels = " · ".join(INTEREST_LABELS[key] for key in interests)

    if recommendations:
        reason_lines = "\n".join(
            f"{index}. {item.place.emoji} <b>{item.place.title}</b>\n"
            f"   ↳ {' · '.join(item.reasons)}"
            for index, item in enumerate(page.items, start=1)
        )
        details = (
            "<b>Почему эти места:</b>\n"
            f"{reason_lines}\n\n"
            "Посещённые, уже пройденные в маршрутах и отмеченные "
            "«Не интересно» места исключены. Избранное, история посещений "
            "и пройденных маршрутов помогают ранжировать похожие новые места."
        )
    else:
        details = (
            "Все подходящие места уже посещены, пройдены в маршрутах "
            "или скрыты."
        )

    await callback.message.edit_text(
        "🎯 <b>Для меня</b>\n\n"
        f"Ваши интересы: {labels}\n"
        f"Подобрано новых мест: {page.total_items} · "
        f"страница {page.number}/{page.total_pages}.\n\n"
        f"{details}",
        reply_markup=personalized_places_keyboard(place_page),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:personal")
async def personal_recommendations(
    callback: CallbackQuery,
    state: FSMContext,
    dismissed_repo: DismissedRepository,
    favorites_repo: FavoritesRepository,
    interests_repo: InterestsRepository,
    visited_repo: VisitedRepository,
,
    completed_routes_repo: CompletedRoutesRepository) -> None:
    previous_state = await state.get_state()
    await state.clear()
    if previous_state in LOCATION_REQUEST_STATES:
        await callback.message.answer(
            "Запрос геопозиции отменён.",
            reply_markup=ReplyKeyboardRemove(),
        )

    await show_personal_page(
        callback,
        dismissed_repo,
        favorites_repo,
        interests_repo,
        visited_repo,
        completed_routes_repo,
        0,
    )


@router.callback_query(F.data.startswith("personalpage:"))
async def personal_recommendations_page(
    callback: CallbackQuery,
    dismissed_repo: DismissedRepository,
    favorites_repo: FavoritesRepository,
    interests_repo: InterestsRepository,
    visited_repo: VisitedRepository,
,
    completed_routes_repo: CompletedRoutesRepository) -> None:
    try:
        page_index = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, AttributeError):
        await callback.answer("Некорректная страница.", show_alert=True)
        return

    await show_personal_page(
        callback,
        dismissed_repo,
        favorites_repo,
        interests_repo,
        visited_repo,
        completed_routes_repo,
        page_index,
    )


@router.callback_query(F.data == "personalroute:start")
async def personal_route_start(
    callback: CallbackQuery,
    state: FSMContext,
    interests_repo: InterestsRepository,
) -> None:
    previous_state = await state.get_state()
    await state.clear()
    if previous_state in LOCATION_REQUEST_STATES:
        await callback.message.answer(
            "Запрос геопозиции отменён.",
            reply_markup=ReplyKeyboardRemove(),
        )

    catalog = current_catalog()
    interests = await interests_repo.list_interests(
        callback.from_user.id,
        catalog.slug,
    )
    if not interests:
        await callback.answer(
            "Сначала выберите хотя бы один интерес.",
            show_alert=True,
        )
        return

    await state.set_state(PersonalRouteFlow.waiting_duration)

    await callback.message.edit_text(
        "🪄 <b>Маршрут для меня</b>\n\n"
        "Сколько времени у вас есть? Можно также один раз передать "
        "геопозицию — тогда пеший бюджет начнётся от текущей точки. "
        "Координаты не сохраняются.",
        reply_markup=personal_route_duration_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "personalroute:location")
async def personal_route_request_location(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.update_data(
        start_latitude=None,
        start_longitude=None,
    )
    await state.set_state(PersonalRouteFlow.waiting_location)
    await callback.message.answer(
        "📍 <b>Старт персонального маршрута</b>\n\n"
        "Передайте текущую геопозицию один раз. Она будет использована "
        "только для расчёта первой точки и пешего времени этого маршрута.",
        reply_markup=request_location_keyboard(),
    )
    await callback.answer()


@router.message(PersonalRouteFlow.waiting_location, F.location)
async def personal_route_location(
    message: Message,
    state: FSMContext,
) -> None:
    location = message.location
    if location is None:
        await message.answer("Не удалось прочитать геопозицию.")
        return

    await state.update_data(
        start_latitude=location.latitude,
        start_longitude=location.longitude,
    )
    await state.set_state(PersonalRouteFlow.waiting_duration)
    await message.answer(
        "✅ Геопозиция принята и будет использована только для этого маршрута.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer(
        "Теперь выберите, сколько времени есть:",
        reply_markup=personal_route_duration_keyboard(location_selected=True),
    )


@router.message(PersonalRouteFlow.waiting_location, F.text == "Отмена")
async def personal_route_location_cancel(
    message: Message,
    state: FSMContext,
) -> None:
    await state.clear()
    await state.set_state(PersonalRouteFlow.waiting_duration)
    await message.answer(
        "Геопозиция не используется.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer(
        "Выберите время для персонального маршрута:",
        reply_markup=personal_route_duration_keyboard(),
    )


@router.message(PersonalRouteFlow.waiting_location)
async def personal_route_location_invalid(message: Message) -> None:
    await message.answer(
        "Нажмите «📍 Отправить мою геопозицию» или выберите «Отмена».",
        reply_markup=request_location_keyboard(),
    )


@router.callback_query(F.data.startswith("personalroute:duration:"))
async def personal_route_duration(
    callback: CallbackQuery,
    state: FSMContext,
    dismissed_repo: DismissedRepository,
    favorites_repo: FavoritesRepository,
    interests_repo: InterestsRepository,
    visited_repo: VisitedRepository,
,
    completed_routes_repo: CompletedRoutesRepository) -> None:
    try:
        budget_minutes = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, AttributeError):
        await callback.answer("Некорректное время.", show_alert=True)
        return

    if budget_minutes not in {120, 240, 360}:
        await callback.answer(
            "Такой вариант времени не поддерживается.",
            show_alert=True,
        )
        return

    data = await state.get_data()
    start_latitude = data.get("start_latitude")
    start_longitude = data.get("start_longitude")
    if start_latitude is not None and not isinstance(start_latitude, (int, float)):
        await state.clear()
        await callback.answer(
            "Некорректная геопозиция. Соберите маршрут заново.",
            show_alert=True,
        )
        return
    if start_longitude is not None and not isinstance(start_longitude, (int, float)):
        await state.clear()
        await callback.answer(
            "Некорректная геопозиция. Соберите маршрут заново.",
            show_alert=True,
        )
        return

    catalog = current_catalog()
    interests = await interests_repo.list_interests(
        callback.from_user.id,
        catalog.slug,
    )
    if not interests:
        await state.clear()
        await callback.answer(
            "Сначала выберите хотя бы один интерес.",
            show_alert=True,
        )
        return

    dismissed_slugs = await dismissed_repo.list_place_slugs(
        callback.from_user.id,
        catalog.slug,
    )
    favorite_slugs = await favorites_repo.list_place_slugs(
        callback.from_user.id,
        catalog.slug,
    )
    visited_slugs = await visited_repo.list_place_slugs(
        callback.from_user.id,
        catalog.slug,
    )
    completed_snapshots = await completed_routes_repo.list_snapshots(
        callback.from_user.id,
        catalog.slug,
    )
    completed_route_place_slugs = {
        slug
        for snapshot in completed_snapshots
        for slug in snapshot.place_slugs
    }
    route = build_personal_route(
        catalog,
        interests,
        budget_minutes=budget_minutes,
        favorite_slugs=favorite_slugs,
        visited_slugs=visited_slugs,
        completed_route_place_slugs=completed_route_place_slugs,
        dismissed_slugs=dismissed_slugs,
        start_latitude=(
            float(start_latitude)
            if start_latitude is not None
            else None
        ),
        start_longitude=(
            float(start_longitude)
            if start_longitude is not None
            else None
        ),
    )
    location_used = start_latitude is not None and start_longitude is not None
    await state.clear()

    if route is None:
        await callback.message.edit_text(
            "🎯 Не удалось собрать персональный маршрут под эти условия. "
            "Если использовалась геопозиция, текущая точка могла оказаться "
            "слишком далеко для выбранного бюджета времени.",
            reply_markup=personal_route_duration_keyboard(),
        )
        await callback.answer()
        return

    stops = "\n".join(
        f"{index}. {place.emoji} {place.title} — ~{place.visit_minutes} мин"
        for index, place in enumerate(route.places, start=1)
    )
    hours, minutes = divmod(route.estimated_minutes, 60)

    await callback.message.edit_text(
        f"🪄 <b>{PERSONAL_ROUTE_LABEL}</b>\n\n"
        f"Бюджет: {route.budget_minutes // 60} ч\n"
        + ("Старт: от вашей геопозиции\n" if location_used else "")
        + f"Оценка маршрута: ~{hours} ч {minutes:02d} мин\n"
        f"Пешком по расчёту: ~{route.distance_km:g} км\n"
        f"Точек: {len(route.places)}\n\n"
        f"<b>Маршрут:</b>\n{stops}\n\n"
        "Использованы текущие интересы, избранное, история посещений "
        "и пройденных маршрутов; уже посещённые, пройденные и отмеченные "
        "«Не интересно» места исключены. "
        "Геопозиция после расчёта не сохраняется.",
        reply_markup=generated_route_keyboard(
            route.places,
            save_callback=build_save_callback(catalog, route),
            restart_callback="personalroute:start",
            restart_text="🪄 Собрать заново",
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "pref:edit")
async def edit_interests(
    callback: CallbackQuery,
    interests_repo: InterestsRepository,
) -> None:
    catalog = current_catalog()
    interests = await interests_repo.list_interests(
        callback.from_user.id,
        catalog.slug,
    )
    await callback.message.edit_text(
        "⚙️ <b>Ваши интересы</b>\n\n"
        "Нажимайте на пункты, чтобы включать или выключать их. "
        "Изменения сохраняются сразу.",
        reply_markup=interests_keyboard(interests),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pref:toggle:"))
async def toggle_interest(
    callback: CallbackQuery,
    interests_repo: InterestsRepository,
) -> None:
    interest = callback.data.rsplit(":", 1)[1]
    if interest not in INTEREST_LABELS:
        await callback.answer("Неизвестный интерес.", show_alert=True)
        return

    catalog = current_catalog()
    interests = await interests_repo.list_interests(
        callback.from_user.id,
        catalog.slug,
    )

    if interest in interests:
        await interests_repo.remove(callback.from_user.id, catalog.slug, interest)
    else:
        await interests_repo.add(callback.from_user.id, catalog.slug, interest)

    updated = await interests_repo.list_interests(
        callback.from_user.id,
        catalog.slug,
    )
    await callback.message.edit_text(
        "⚙️ <b>Ваши интересы</b>\n\n"
        f"Выбрано: {len(updated)}. Изменения сохранены.",
        reply_markup=interests_keyboard(updated),
    )
    await callback.answer()


@router.callback_query(F.data == "pref:done")
async def finish_interests(
    callback: CallbackQuery,
    dismissed_repo: DismissedRepository,
    favorites_repo: FavoritesRepository,
    interests_repo: InterestsRepository,
    visited_repo: VisitedRepository,
,
    completed_routes_repo: CompletedRoutesRepository) -> None:
    catalog = current_catalog()
    interests = await interests_repo.list_interests(
        callback.from_user.id,
        catalog.slug,
    )
    if not interests:
        await callback.answer("Выберите хотя бы один интерес.", show_alert=True)
        return

    await show_personal_page(
        callback,
        dismissed_repo,
        favorites_repo,
        interests_repo,
        visited_repo,
        completed_routes_repo,
        0,
    )


@router.callback_query(F.data == "menu:nearby")
async def near_me_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(NearbyFlow.waiting_location)
    await callback.message.answer(
        "📡 <b>Рядом со мной</b>\n\n"
        "Передайте текущую геопозицию, и я покажу ближайшие места из каталога "
        "в радиусе 10 км. Координаты не сохраняются.",
        reply_markup=request_location_keyboard(),
    )
    await callback.answer()


@router.message(NearbyFlow.waiting_location, F.location)
async def near_me_location(message: Message, state: FSMContext) -> None:
    location = message.location
    if location is None:
        await message.answer("Не удалось прочитать геопозицию.")
        return

    catalog = current_catalog()
    nearby_items = catalog.nearby_from_coordinates(
        location.latitude,
        location.longitude,
    )
    await state.clear()

    await message.answer(
        "✅ Геопозиция принята.",
        reply_markup=ReplyKeyboardRemove(),
    )

    if not nearby_items:
        await message.answer(
            f"В радиусе 10 км не нашлось точек из каталога «{catalog.name}». "
            "Возможно, вы находитесь за пределами основной зоны каталога.",
            reply_markup=home_keyboard(),
        )
        return

    lines = [
        f"{index}. {place.emoji} {place.title} — ~{distance:.1f} км"
        for index, (place, distance) in enumerate(nearby_items, start=1)
    ]
    places = tuple(place for place, _ in nearby_items)

    await message.answer(
        "📡 <b>Ближайшие места</b>\n\n" + "\n".join(lines),
        reply_markup=places_keyboard(
            places,
            back_callback="menu:home",
            back_text="← Главное меню",
            place_context=home_context(),
        ),
    )


@router.message(NearbyFlow.waiting_location, F.text == "Отмена")
async def near_me_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    catalog = current_catalog()
    await message.answer(
        "Запрос геопозиции отменён.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer(home_text(catalog), reply_markup=home_keyboard())


@router.message(NearbyFlow.waiting_location)
async def near_me_invalid(message: Message) -> None:
    await message.answer(
        "Нажмите «📍 Отправить мою геопозицию» или выберите «Отмена».",
        reply_markup=request_location_keyboard(),
    )


@router.callback_query(F.data == "builder:start")
async def route_builder_start(callback: CallbackQuery, state: FSMContext) -> None:
    previous_state = await state.get_state()
    await state.clear()
    if previous_state in LOCATION_REQUEST_STATES:
        await callback.message.answer(
            "Запрос геопозиции отменён.",
            reply_markup=ReplyKeyboardRemove(),
        )

    await state.set_state(RouteBuilderFlow.waiting_duration)
    await callback.message.edit_text(
        "🪄 <b>Собрать маршрут</b>\n\n"
        "Сколько времени вы хотите провести на прогулке?\n\n"
        "Можно также поделиться геопозицией — тогда маршрут начнётся с ближайшей "
        "подходящей точки. В расчёт входят посещение и пешие переходы.",
        reply_markup=route_duration_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "builder:location")
async def route_builder_request_location(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.set_state(RouteBuilderFlow.waiting_location)
    await callback.message.answer(
        "📍 <b>Старт от вашей геопозиции</b>\n\n"
        "Нажмите кнопку ниже, чтобы один раз передать текущую точку. "
        "Координаты используются только для расчёта этого маршрута и не сохраняются.",
        reply_markup=request_location_keyboard(),
    )
    await callback.answer()


@router.message(RouteBuilderFlow.waiting_location, F.location)
async def route_builder_location(message: Message, state: FSMContext) -> None:
    location = message.location
    if location is None:
        await message.answer("Не удалось прочитать геопозицию.")
        return

    await state.update_data(
        start_latitude=location.latitude,
        start_longitude=location.longitude,
    )
    await state.set_state(RouteBuilderFlow.waiting_duration)
    await message.answer(
        "✅ Геопозиция принята.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer(
        "Теперь выберите, сколько времени есть на прогулку:",
        reply_markup=route_duration_keyboard(location_selected=True),
    )


@router.message(RouteBuilderFlow.waiting_location, F.text == "Отмена")
async def route_builder_location_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    catalog = current_catalog()
    await message.answer(
        "Запрос геопозиции отменён.",
        reply_markup=ReplyKeyboardRemove(),
    )
    await message.answer(home_text(catalog), reply_markup=home_keyboard())


@router.message(RouteBuilderFlow.waiting_location)
async def route_builder_location_invalid(message: Message) -> None:
    await message.answer(
        "Для старта от текущего места нажмите «📍 Отправить мою геопозицию» "
        "или выберите «Отмена».",
        reply_markup=request_location_keyboard(),
    )


@router.callback_query(F.data.startswith("builder:duration:"))
async def route_builder_duration(callback: CallbackQuery, state: FSMContext) -> None:
    raw_minutes = callback.data.rsplit(":", 1)[1]
    try:
        budget_minutes = int(raw_minutes)
    except ValueError:
        await callback.answer("Некорректное время.", show_alert=True)
        return

    if budget_minutes not in {120, 240, 360}:
        await callback.answer("Такой вариант времени не поддерживается.", show_alert=True)
        return

    await state.update_data(budget_minutes=budget_minutes)
    await state.set_state(RouteBuilderFlow.waiting_interest)
    await callback.message.edit_text(
        "🪄 <b>Что вам интереснее?</b>\n\n"
        f"Доступное время: <b>{budget_minutes // 60} ч</b>.\n"
        "Выберите акцент маршрута:",
        reply_markup=route_interest_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("builder:interest:"))
async def route_builder_interest(callback: CallbackQuery, state: FSMContext) -> None:
    interest = callback.data.rsplit(":", 1)[1]
    if interest not in INTEREST_LABELS:
        await callback.answer("Неизвестный тип маршрута.", show_alert=True)
        return

    data = await state.get_data()
    budget_minutes = data.get("budget_minutes")
    if not isinstance(budget_minutes, int) or budget_minutes not in {120, 240, 360}:
        await state.clear()
        await callback.answer("Начните сбор маршрута заново.", show_alert=True)
        return

    start_latitude = data.get("start_latitude")
    start_longitude = data.get("start_longitude")
    if start_latitude is not None and not isinstance(start_latitude, (int, float)):
        await state.clear()
        await callback.answer("Некорректная геопозиция. Начните заново.", show_alert=True)
        return
    if start_longitude is not None and not isinstance(start_longitude, (int, float)):
        await state.clear()
        await callback.answer("Некорректная геопозиция. Начните заново.", show_alert=True)
        return

    catalog = current_catalog()
    route = build_route(
        catalog,
        budget_minutes=budget_minutes,
        interest=interest,
        start_latitude=float(start_latitude) if start_latitude is not None else None,
        start_longitude=float(start_longitude) if start_longitude is not None else None,
    )
    location_used = start_latitude is not None and start_longitude is not None
    await state.clear()

    if route is None or not route.places:
        await callback.message.edit_text(
            "Не удалось собрать маршрут под эти условия из текущего каталога.",
            reply_markup=back_home_keyboard(),
        )
        await callback.answer()
        return

    stops = "\n".join(
        f"{index}. {place.emoji} {place.title} — ~{place.visit_minutes} мин"
        for index, place in enumerate(route.places, start=1)
    )
    hours, minutes = divmod(route.estimated_minutes, 60)

    await callback.message.edit_text(
        f"🪄 <b>{INTEREST_LABELS[route.interest]}</b>\n\n"
        f"Бюджет: {route.budget_minutes // 60} ч\n"
        + ("Старт: от вашей геопозиции\n" if location_used else "")
        + f"Оценка маршрута: ~{hours} ч {minutes:02d} мин\n"
        f"Пешком по расчёту: ~{route.distance_km:g} км\n"
        f"Точек: {len(route.places)}\n\n"
        f"<b>Маршрут:</b>\n{stops}\n\n"
        "Время переходов рассчитано ориентировочно для пешей скорости 4,5 км/ч. "
        "Фактический путь может отличаться из-за мостов, переходов и дорожной сети.",
        reply_markup=generated_route_keyboard(
            route.places,
            save_callback=build_save_callback(catalog, route),
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("savegen:"))
async def save_generated_route(
    callback: CallbackQuery,
    saved_routes_repo: SavedRoutesRepository,
) -> None:
    catalog = current_catalog()
    try:
        snapshot = parse_save_callback(callback.data, catalog)
    except ValueError:
        await callback.answer(
            "Этот маршрут устарел. Соберите его заново.",
            show_alert=True,
        )
        return

    saved = await saved_routes_repo.save(
        callback.from_user.id,
        catalog.slug,
        snapshot.interest,
        snapshot.budget_minutes,
        tuple(place.slug for place in snapshot.places),
    )
    if snapshot.interest == PERSONAL_ROUTE_INTEREST:
        reply_markup = generated_route_keyboard(
            snapshot.places,
            restart_callback="personalroute:start",
            restart_text="🪄 Собрать заново",
        )
    elif snapshot.interest == PLACE_ROUTE_INTEREST:
        reply_markup = generated_route_keyboard(
            snapshot.places,
            restart_callback=place_route_callback(
                snapshot.places[0].slug,
                "d",
            ),
            restart_text="🪄 Другой бюджет",
        )
    else:
        reply_markup = generated_route_keyboard(snapshot.places)

    await callback.message.edit_reply_markup(reply_markup=reply_markup)
    await callback.answer(f"Маршрут сохранён · {saved.route_id[:6]}")


async def show_saved_routes_page(
    callback: CallbackQuery,
    saved_routes_repo: SavedRoutesRepository,
    completed_routes_repo: CompletedRoutesRepository,
    page_index: int,
) -> None:
    catalog = current_catalog()
    routes = await saved_routes_repo.list_routes(
        callback.from_user.id,
        catalog.slug,
    )

    if not routes:
        await callback.message.edit_text(
            "🧭 <b>Сохранённые маршруты</b>\n\n"
            "Здесь пока пусто. Соберите маршрут и нажмите "
            "«💾 Сохранить маршрут».",
            reply_markup=profile_keyboard(),
        )
        await callback.answer()
        return

    page = paginate(routes, page_index)
    completed_route_ids = frozenset(
        await completed_routes_repo.list_route_ids(
            callback.from_user.id,
            catalog.slug,
        )
    )
    await callback.message.edit_text(
        "🧭 <b>Сохранённые маршруты</b>\n\n"
        f"Сохранено: {page.total_items} · "
        f"страница {page.number}/{page.total_pages}.",
        reply_markup=saved_routes_keyboard(
            page,
            completed_route_ids=completed_route_ids,
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:savedroutes")
async def saved_routes(
    callback: CallbackQuery,
    saved_routes_repo: SavedRoutesRepository,
    completed_routes_repo: CompletedRoutesRepository,
) -> None:
    await show_saved_routes_page(
        callback,
        saved_routes_repo,
        completed_routes_repo,
        0,
    )


@router.callback_query(F.data.startswith("savedroutes:"))
async def saved_routes_page(
    callback: CallbackQuery,
    saved_routes_repo: SavedRoutesRepository,
    completed_routes_repo: CompletedRoutesRepository,
) -> None:
    try:
        page_index = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, AttributeError):
        await callback.answer("Некорректная страница.", show_alert=True)
        return

    await show_saved_routes_page(
        callback,
        saved_routes_repo,
        completed_routes_repo,
        page_index,
    )


@router.callback_query(F.data.startswith("savedroute:complete:"))
async def complete_saved_route_callback(
    callback: CallbackQuery,
    saved_routes_repo: SavedRoutesRepository,
    visited_repo: VisitedRepository,
    completed_routes_repo: CompletedRoutesRepository,
) -> None:
    route_id = callback.data.removeprefix("savedroute:complete:").strip()
    if not route_id:
        await callback.answer("Некорректный маршрут.", show_alert=True)
        return

    catalog = current_catalog()
    result = await complete_saved_route(
        user_id=callback.from_user.id,
        city_slug=catalog.slug,
        route_id=route_id,
        saved_routes=saved_routes_repo,
        visited=visited_repo,
        catalog=catalog,
        completed_routes=completed_routes_repo,
    )
    if result is None:
        await callback.answer(
            "Сохранённый маршрут не найден.",
            show_alert=True,
        )
        return

    await callback.answer(
        "Маршрут отмечен как пройденный. "
        f"Новых мест: {result.added}; "
        f"уже были отмечены: {result.already_visited}; "
        f"недоступно: {result.unavailable}.",
        show_alert=True,
    )


@router.callback_query(F.data.startswith("savedroute:delete:"))
async def delete_saved_route(
    callback: CallbackQuery,
    saved_routes_repo: SavedRoutesRepository,
    completed_routes_repo: CompletedRoutesRepository,
) -> None:
    route_id = callback.data.removeprefix("savedroute:delete:").strip()
    catalog = current_catalog()
    if not route_id:
        await callback.answer("Некорректный маршрут.", show_alert=True)
        return

    await saved_routes_repo.remove(
        callback.from_user.id,
        catalog.slug,
        route_id,
    )
    await show_saved_routes_page(
        callback,
        saved_routes_repo,
        completed_routes_repo,
        0,
    )


@router.callback_query(F.data.startswith("savedroute:"))
async def saved_route_card(
    callback: CallbackQuery,
    saved_routes_repo: SavedRoutesRepository,
    completed_routes_repo: CompletedRoutesRepository,
) -> None:
    route_id = callback.data.removeprefix("savedroute:").strip()
    catalog = current_catalog()
    route = await saved_routes_repo.get(
        callback.from_user.id,
        catalog.slug,
        route_id,
    )
    if route is None:
        await callback.answer(
            "Сохранённый маршрут не найден.",
            show_alert=True,
        )
        return

    places = tuple(
        place
        for slug in route.place_slugs
        if (place := catalog.place_by_slug(slug)) is not None
    )
    label = route_interest_label(route.interest)
    stops = "\n".join(
        f"{index}. {place.emoji} {place.title}"
        for index, place in enumerate(places, start=1)
    )
    unavailable_count = len(route.place_slugs) - len(places)

    body = (
        f"🧭 <b>{label}</b>\n\n"
        f"Бюджет: {route.budget_minutes // 60} ч\n"
        f"Точек доступно: {len(places)}/{len(route.place_slugs)}\n\n"
    )
    if places:
        body += f"<b>Маршрут:</b>\n{stops}"
    else:
        body += "Все точки этого snapshot сейчас отсутствуют в каталоге."

    if unavailable_count:
        body += (
            "\n\nЧасть точек была удалена или переименована "
            "в текущем каталоге и пропущена."
        )

    is_completed = await completed_routes_repo.contains(
        callback.from_user.id,
        catalog.slug,
        route.route_id,
    )
    await callback.message.edit_text(
        body,
        reply_markup=saved_route_details_keyboard(
            route,
            places,
            is_completed=is_completed,
        ),
    )
    await callback.answer()


async def show_completed_routes_page(
    callback: CallbackQuery,
    completed_routes_repo: CompletedRoutesRepository,
    page_index: int,
) -> None:
    catalog = current_catalog()
    routes = await completed_routes_repo.list_snapshots(callback.from_user.id, catalog.slug)
    if not routes:
        await callback.message.edit_text(
            "🏁 <b>Пройденные маршруты</b>\n\nИстория пока пуста.",
            reply_markup=profile_keyboard(),
        )
        await callback.answer()
        return
    page = paginate(routes, page_index)
    await callback.message.edit_text(
        "🏁 <b>Пройденные маршруты</b>\n\n"
        f"Пройдено: {page.total_items} · страница {page.number}/{page.total_pages}.",
        reply_markup=completed_routes_keyboard(page),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:completedroutes")
async def completed_routes(
    callback: CallbackQuery,
    completed_routes_repo: CompletedRoutesRepository,
) -> None:
    await show_completed_routes_page(callback, completed_routes_repo, 0)


@router.callback_query(F.data.startswith("completedroutes:"))
async def completed_routes_page(
    callback: CallbackQuery,
    completed_routes_repo: CompletedRoutesRepository,
) -> None:
    try:
        page_index = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, AttributeError):
        await callback.answer("Некорректная страница.", show_alert=True)
        return
    await show_completed_routes_page(callback, completed_routes_repo, page_index)


@router.callback_query(F.data.startswith("completedroute:"))
async def completed_route_card(
    callback: CallbackQuery,
    completed_routes_repo: CompletedRoutesRepository,
) -> None:
    route_id = callback.data.removeprefix("completedroute:").strip()
    catalog = current_catalog()
    route = await completed_routes_repo.get_snapshot(callback.from_user.id, catalog.slug, route_id)
    if route is None:
        await callback.answer("Пройденный маршрут не найден.", show_alert=True)
        return
    places = tuple(
        place for slug in route.place_slugs
        if (place := catalog.place_by_slug(slug)) is not None
    )
    stops = "\n".join(
        f"{index}. {place.emoji} {place.title}"
        for index, place in enumerate(places, start=1)
    )
    unavailable = len(route.place_slugs) - len(places)
    body = (
        f"🏁 <b>{route_interest_label(route.interest)}</b>\n\n"
        f"Пройден: {route.completed_at}\n"
        f"Бюджет: {route.budget_minutes // 60} ч\n"
        f"Точек доступно: {len(places)}/{len(route.place_slugs)}\n\n"
        + (f"<b>Маршрут:</b>\n{stops}" if places else "Все точки snapshot сейчас отсутствуют в каталоге.")
    )
    if unavailable:
        body += "\n\nЧасть точек была удалена или переименована в текущем каталоге."
    await callback.message.edit_text(
        body,
        reply_markup=completed_route_details_keyboard(route, places),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:routes")
async def menu_routes(callback: CallbackQuery) -> None:
    catalog = current_catalog()
    await callback.message.edit_text(
        "🗺 <b>Готовые маршруты</b>\n\n"
        f"Первый набор прогулок по городу {catalog.name}:",
        reply_markup=routes_keyboard(catalog.routes),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("route:"))
async def route_card(callback: CallbackQuery) -> None:
    catalog = current_catalog()
    slug = callback.data.split(":", 1)[1]
    route = catalog.route_by_slug(slug)
    if route is None:
        await callback.answer("Маршрут не найден.", show_alert=True)
        return

    route_places = tuple(
        place
        for place_slug in route.place_slugs
        if (place := catalog.place_by_slug(place_slug)) is not None
    )
    stops = "\n".join(
        f"{index}. {place.title}"
        for index, place in enumerate(route_places, start=1)
    )

    await callback.message.edit_text(
        f"🧭 <b>{route.title}</b>\n\n"
        f"{route.summary}\n\n"
        f"⏱ ~{route.duration_minutes // 60} ч {route.duration_minutes % 60:02d} мин\n"
        f"🚶 ~{route.distance_km:g} км\n\n"
        f"<b>Точки:</b>\n{stops}\n\n"
        "Ниже можно открыть пешеходный маршрут в Google Maps. "
        "Длинные прогулки разбиваются на несколько последовательных частей.",
        reply_markup=route_details_keyboard(route_places),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:excursions")
async def excursions(callback: CallbackQuery) -> None:
    catalog = current_catalog()
    providers = get_excursion_providers(
        get_settings(),
        city_slug=catalog.slug,
    )
    if not providers:
        await callback.message.edit_text(
            "🎟 <b>Экскурсии</b>\n\n"
            f"Для города {catalog.name} live-провайдеры пока не подключены.",
            reply_markup=back_home_keyboard(),
        )
        await callback.answer()
        return
    freshness = max(provider.checked_at for provider in providers)
    source_lines = "\n".join(
        f"• <b>{provider.name}</b> — официальный live-каталог"
        for provider in providers
    )

    await callback.message.edit_text(
        f"🎟 <b>Экскурсии · {catalog.name}</b>\n\n"
        f"{source_lines}\n\n"
        "Цены, расписание и наличие мест открываются напрямую у провайдера — "
        "бот не копирует их в локальную базу и не показывает устаревшие значения.\n\n"
        f"Источники проверены: <b>{freshness.strftime('%d.%m.%Y')}</b>.",
        reply_markup=excursion_providers_keyboard(providers),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:events")
async def events(callback: CallbackQuery) -> None:
    catalog = current_catalog()
    providers = get_event_providers(
        get_settings(),
        city_slug=catalog.slug,
    )
    if not providers:
        await callback.message.edit_text(
            "🎭 <b>События</b>\n\n"
            f"Для города {catalog.name} live-афиша пока не подключена.",
            reply_markup=back_home_keyboard(),
        )
        await callback.answer()
        return
    freshness = max(provider.checked_at for provider in providers)
    source_lines = "\n".join(
        f"• <b>{provider.name}</b> — live-афиша"
        for provider in providers
    )

    await callback.message.edit_text(
        f"🎭 <b>События · {catalog.name}</b>\n\n"
        f"{source_lines}\n\n"
        "Даты, цены и наличие билетов открываются напрямую у источника. "
        "Бот не сохраняет динамическую афишу как постоянные локальные данные.\n\n"
        f"Источники проверены: <b>{freshness.strftime('%d.%m.%Y')}</b>.",
        reply_markup=event_providers_keyboard(providers),
    )
    await callback.answer()


async def show_dismissed_page(
    callback: CallbackQuery,
    dismissed_repo: DismissedRepository,
    page_index: int,
) -> None:
    catalog = current_catalog()
    slugs = await dismissed_repo.list_place_slugs(
        callback.from_user.id,
        catalog.slug,
    )
    places = tuple(
        place
        for slug in slugs
        if (place := catalog.place_by_slug(slug)) is not None
    )

    if not places:
        await callback.message.edit_text(
            "🙈 <b>Скрытые рекомендации</b>\n\n"
            "Здесь пока нет доступных скрытых мест. "
            "В карточке места можно нажать «🙈 Не интересно», "
            "а затем вернуть его отсюда.",
            reply_markup=profile_keyboard(),
        )
        await callback.answer()
        return

    page = paginate(places, page_index)
    await callback.message.edit_text(
        "🙈 <b>Скрытые рекомендации</b>\n\n"
        f"Скрыто доступных мест: {page.total_items} · "
        f"страница {page.number}/{page.total_pages}.\n\n"
        "Откройте карточку места и нажмите «↩️ Вернуть в рекомендации».",
        reply_markup=paginated_places_keyboard(
            page,
            page_callback_prefix="dismissedpage",
            back_callback="menu:profile",
            back_text="← Мой гид",
            place_context=dismissed_context(page.index),
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:dismissed")
async def dismissed_places(
    callback: CallbackQuery,
    dismissed_repo: DismissedRepository,
) -> None:
    await show_dismissed_page(callback, dismissed_repo, 0)


@router.callback_query(F.data.startswith("dismissedpage:"))
async def dismissed_places_page(
    callback: CallbackQuery,
    dismissed_repo: DismissedRepository,
) -> None:
    try:
        page_index = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, AttributeError):
        await callback.answer("Некорректная страница.", show_alert=True)
        return

    await show_dismissed_page(callback, dismissed_repo, page_index)


async def show_favorites_page(
    callback: CallbackQuery,
    favorites_repo: FavoritesRepository,
    page_index: int,
) -> None:
    catalog = current_catalog()
    slugs = await favorites_repo.list_place_slugs(callback.from_user.id, catalog.slug)
    places = tuple(
        place
        for slug in slugs
        if (place := catalog.place_by_slug(slug)) is not None
    )

    if not places:
        await callback.message.edit_text(
            "❤️ <b>Избранное</b>\n\n"
            "Здесь пока пусто. Откройте карточку места и нажмите «❤️ В избранное».",
            reply_markup=back_home_keyboard(),
        )
        await callback.answer()
        return

    page = paginate(places, page_index)
    await callback.message.edit_text(
        "❤️ <b>Избранное</b>\n\n"
        f"Сохранено: {page.total_items} · страница {page.number}/{page.total_pages}.",
        reply_markup=paginated_places_keyboard(
            page,
            page_callback_prefix="favpage",
            back_callback="menu:home",
            back_text="← Главное меню",
            place_context=favorites_context(page.index),
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:favorites")
async def favorites(
    callback: CallbackQuery,
    favorites_repo: FavoritesRepository,
) -> None:
    await show_favorites_page(callback, favorites_repo, 0)


@router.callback_query(F.data.startswith("favpage:"))
async def favorites_page(
    callback: CallbackQuery,
    favorites_repo: FavoritesRepository,
) -> None:
    try:
        page_index = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, AttributeError):
        await callback.answer("Некорректная страница.", show_alert=True)
        return

    await show_favorites_page(callback, favorites_repo, page_index)


async def show_visited_page(
    callback: CallbackQuery,
    visited_repo: VisitedRepository,
    page_index: int,
) -> None:
    catalog = current_catalog()
    slugs = await visited_repo.list_place_slugs(
        callback.from_user.id,
        catalog.slug,
    )
    places = tuple(
        place
        for slug in slugs
        if (place := catalog.place_by_slug(slug)) is not None
    )

    if not places:
        await callback.message.edit_text(
            "✅ <b>Посещённые</b>\n\n"
            "Здесь пока пусто. В карточке места нажмите «✅ Уже был».",
            reply_markup=back_home_keyboard(),
        )
        await callback.answer()
        return

    page = paginate(places, page_index)
    await callback.message.edit_text(
        "✅ <b>Посещённые</b>\n\n"
        f"Отмечено: {page.total_items} · "
        f"страница {page.number}/{page.total_pages}.",
        reply_markup=visited_places_keyboard(page),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:visited")
async def visited_places(
    callback: CallbackQuery,
    visited_repo: VisitedRepository,
) -> None:
    await show_visited_page(callback, visited_repo, 0)


@router.callback_query(F.data.startswith("visitedpage:"))
async def visited_places_page(
    callback: CallbackQuery,
    visited_repo: VisitedRepository,
) -> None:
    try:
        page_index = int(callback.data.rsplit(":", 1)[1])
    except (ValueError, AttributeError):
        await callback.answer("Некорректная страница.", show_alert=True)
        return

    await show_visited_page(callback, visited_repo, page_index)


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery) -> None:
    await callback.answer()


@router.callback_query(F.data == "menu:search")
async def search(callback: CallbackQuery, state: FSMContext) -> None:
    catalog = current_catalog()
    await state.set_state(SearchFlow.waiting_query)
    await callback.message.edit_text(
        search_prompt(catalog),
        reply_markup=back_home_keyboard(),
    )
    await callback.answer()


@router.message(SearchFlow.waiting_query, F.text)
async def search_query(message: Message, state: FSMContext) -> None:
    catalog = current_catalog()
    query = message.text.strip()
    results = catalog.search_places(query)
    await state.clear()

    if not results:
        await message.answer(
            search_not_found_text(query),
            reply_markup=back_home_keyboard(),
        )
        return

    await message.answer(
        search_results_text(query, len(results)),
        reply_markup=places_keyboard(
            results,
            back_callback="menu:home",
            back_text="← Главное меню",
            place_context=search_context(),
        ),
    )


@router.message(SearchFlow.waiting_query)
async def search_non_text(message: Message) -> None:
    await message.answer("Для поиска отправьте текстовый запрос.")

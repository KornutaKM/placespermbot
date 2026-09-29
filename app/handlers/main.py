from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from app.catalog import CityCatalog, get_catalog
from app.config import get_settings
from app.events import get_event_providers
from app.excursions import get_excursion_providers
from app.keyboards import (
    back_home_keyboard,
    categories_keyboard,
    event_providers_keyboard,
    excursion_providers_keyboard,
    generated_route_keyboard,
    home_keyboard,
    interests_keyboard,
    personalized_places_keyboard,
    place_keyboard,
    places_keyboard,
    request_location_keyboard,
    route_details_keyboard,
    route_duration_keyboard,
    route_interest_keyboard,
    routes_keyboard,
)
from app.planner import INTEREST_LABELS, build_route
from app.recommendations import recommend_places
from app.storage import FavoritesRepository, InterestsRepository

router = Router()


class SearchFlow(StatesGroup):
    waiting_query = State()


class RouteBuilderFlow(StatesGroup):
    waiting_location = State()
    waiting_duration = State()
    waiting_interest = State()


class NearbyFlow(StatesGroup):
    waiting_location = State()


LOCATION_REQUEST_STATES = {
    RouteBuilderFlow.waiting_location.state,
    NearbyFlow.waiting_location.state,
}


def current_catalog() -> CityCatalog:
    return get_catalog(get_settings().city_slug)


def home_text(catalog: CityCatalog) -> str:
    return (
        f"📍 <b>{catalog.name}</b>\n\n"
        "Что хотите сделать?\n\n"
        "Можно выбрать места, готовую прогулку или собрать маршрут под себя."
    )


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    previous_state = await state.get_state()
    await state.clear()
    if previous_state in LOCATION_REQUEST_STATES:
        await message.answer(
            "Запрос геопозиции отменён.",
            reply_markup=ReplyKeyboardRemove(),
        )
    catalog = current_catalog()
    await message.answer(
        "👋 <b>Добро пожаловать!</b>\n\n"
        f"Я — городской гид в Telegram. Сейчас открыт город: {catalog.name}.\n\n"
        + home_text(catalog),
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


@router.callback_query(F.data == "menu:places")
async def menu_places(callback: CallbackQuery) -> None:
    catalog = current_catalog()
    await callback.message.edit_text(
        "📍 <b>Куда сходить</b>\n\nВыберите тип места:",
        reply_markup=categories_keyboard(catalog.category_labels),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cat:"))
async def category(callback: CallbackQuery) -> None:
    catalog = current_catalog()
    key = callback.data.split(":", 1)[1]
    places = catalog.places_for_category(key)
    label = catalog.category_labels.get(key, "Подборка")

    if not places:
        await callback.answer("Для этой подборки пока нет мест.", show_alert=True)
        return

    await callback.message.edit_text(
        f"<b>{label}</b>\n\n"
        "Выберите место. На первом этапе показываем стабильные описательные данные "
        "без непроверенных цен и расписаний.",
        reply_markup=places_keyboard(places),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("place:"))
async def place_card(
    callback: CallbackQuery,
    favorites_repo: FavoritesRepository,
) -> None:
    catalog = current_catalog()
    slug = callback.data.split(":", 1)[1]
    place = catalog.place_by_slug(slug)
    if place is None:
        await callback.answer("Место не найдено.", show_alert=True)
        return

    access = "💸 Бесплатное пространство" if place.is_free else "🎟 Условия посещения уточняются"
    tags = " · ".join(f"#{tag.replace(' ', '_')}" for tag in place.tags)
    is_favorite = await favorites_repo.contains(
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
        f"{tags}",
        reply_markup=place_keyboard(place.slug, is_favorite=is_favorite),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("favorite:"))
async def favorite_action(
    callback: CallbackQuery,
    favorites_repo: FavoritesRepository,
) -> None:
    catalog = current_catalog()
    _, action, slug = callback.data.split(":", 2)
    place = catalog.place_by_slug(slug)

    if place is None or action not in {"add", "remove"}:
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

    await callback.message.edit_reply_markup(
        reply_markup=place_keyboard(place.slug, is_favorite=is_favorite)
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
    slug = callback.data.split(":", 1)[1]
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
            back_callback=f"place:{origin.slug}",
            back_text=f"← {origin.title}",
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:personal")
async def personal_recommendations(
    callback: CallbackQuery,
    interests_repo: InterestsRepository,
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

    places = recommend_places(catalog, interests)
    labels = " · ".join(INTEREST_LABELS[key] for key in interests)

    await callback.message.edit_text(
        "🎯 <b>Для меня</b>\n\n"
        f"Ваши интересы: {labels}\n\n"
        f"Подобрано мест: {len(places)}. Рейтинг строится только по данным каталога.",
        reply_markup=personalized_places_keyboard(places),
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
    interests_repo: InterestsRepository,
) -> None:
    catalog = current_catalog()
    interests = await interests_repo.list_interests(
        callback.from_user.id,
        catalog.slug,
    )
    if not interests:
        await callback.answer("Выберите хотя бы один интерес.", show_alert=True)
        return

    places = recommend_places(catalog, interests)
    labels = " · ".join(INTEREST_LABELS[key] for key in interests)
    await callback.message.edit_text(
        "🎯 <b>Для меня</b>\n\n"
        f"Ваши интересы: {labels}\n\n"
        f"Подобрано мест: {len(places)}.",
        reply_markup=personalized_places_keyboard(places),
    )
    await callback.answer()


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
            "В радиусе 10 км не нашлось точек из текущего каталога Петербурга. "
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
        "🪄 <b>Какой Петербург вам интересен?</b>\n\n"
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
        reply_markup=generated_route_keyboard(route.places),
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
    providers = get_excursion_providers(get_settings())
    freshness = max(provider.checked_at for provider in providers)
    source_lines = "\n".join(
        f"• <b>{provider.name}</b> — официальный live-каталог"
        for provider in providers
    )

    await callback.message.edit_text(
        "🎟 <b>Экскурсии в Санкт-Петербурге</b>\n\n"
        f"{source_lines}\n\n"
        "Цены, расписание и наличие мест открываются напрямую у провайдера — "
        "бот не копирует их в локальную базу и не показывает устаревшие значения.\n\n"
        f"Источники проверены: <b>{freshness.strftime('%d.%m.%Y')}</b>.",
        reply_markup=excursion_providers_keyboard(providers),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:events")
async def events(callback: CallbackQuery) -> None:
    providers = get_event_providers(get_settings())
    freshness = max(provider.checked_at for provider in providers)
    source_lines = "\n".join(
        f"• <b>{provider.name}</b> — live-афиша Петербурга"
        for provider in providers
    )

    await callback.message.edit_text(
        "🎭 <b>События в Санкт-Петербурге</b>\n\n"
        f"{source_lines}\n\n"
        "Даты, цены и наличие билетов открываются напрямую у источника. "
        "Бот не сохраняет динамическую афишу как постоянные локальные данные.\n\n"
        f"Источники проверены: <b>{freshness.strftime('%d.%m.%Y')}</b>.",
        reply_markup=event_providers_keyboard(providers),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:favorites")
async def favorites(
    callback: CallbackQuery,
    favorites_repo: FavoritesRepository,
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

    await callback.message.edit_text(
        f"❤️ <b>Избранное</b>\n\nСохранено мест: {len(places)}.",
        reply_markup=places_keyboard(
            places,
            back_callback="menu:home",
            back_text="← Главное меню",
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:search")
async def search(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SearchFlow.waiting_query)
    await callback.message.edit_text(
        "🔍 <b>Поиск по местам</b>\n\n"
        "Напишите название, тип места, район или интерес.\n\n"
        "Например: <i>Эрмитаж</i>, <i>музей</i>, <i>остров</i>, <i>архитектура</i>.",
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
            f"🔍 По запросу <b>{query}</b> ничего не нашлось.\n\n"
            "Попробуйте название места, «музей», «парк», «архитектура» или район.",
            reply_markup=back_home_keyboard(),
        )
        return

    await message.answer(
        f"🔍 <b>Результаты поиска: {query}</b>\n\n"
        f"Найдено: {len(results)}. Выберите место:",
        reply_markup=places_keyboard(
            results,
            back_callback="menu:home",
            back_text="← Главное меню",
        ),
    )


@router.message(SearchFlow.waiting_query)
async def search_non_text(message: Message) -> None:
    await message.answer("Для поиска отправьте текстовый запрос.")

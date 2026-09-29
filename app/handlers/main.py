from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from app.catalog import CityCatalog, get_catalog
from app.config import get_settings
from app.keyboards import (
    back_home_keyboard,
    categories_keyboard,
    home_keyboard,
    place_keyboard,
    places_keyboard,
    routes_keyboard,
)

router = Router()


def current_catalog() -> CityCatalog:
    return get_catalog(get_settings().city_slug)


def home_text(catalog: CityCatalog) -> str:
    return (
        f"📍 <b>{catalog.name}</b>\n\n"
        "Что хотите сделать?\n\n"
        "Можно выбрать места, готовую прогулку или подборку под настроение."
    )


@router.message(CommandStart())
async def start(message: Message) -> None:
    catalog = current_catalog()
    await message.answer(
        "👋 <b>Добро пожаловать!</b>\n\n"
        f"Я — городской гид в Telegram. Сейчас открыт город: {catalog.name}.\n\n"
        + home_text(catalog),
        reply_markup=home_keyboard(),
    )


@router.callback_query(F.data == "menu:home")
async def menu_home(callback: CallbackQuery) -> None:
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
async def place_card(callback: CallbackQuery) -> None:
    catalog = current_catalog()
    slug = callback.data.split(":", 1)[1]
    place = catalog.place_by_slug(slug)
    if place is None:
        await callback.answer("Место не найдено.", show_alert=True)
        return

    access = "💸 Бесплатное пространство" if place.is_free else "🎟 Условия посещения уточняются"
    tags = " · ".join(f"#{tag.replace(' ', '_')}" for tag in place.tags)

    await callback.message.edit_text(
        f"{place.emoji} <b>{place.title}</b>\n\n"
        f"{place.summary}\n\n"
        f"📍 {place.district}\n"
        f"⏱ Ориентир на посещение: ~{place.visit_minutes} мин\n"
        f"{access}\n\n"
        f"{tags}",
        reply_markup=place_keyboard(place.slug),
    )
    await callback.answer()


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

    titles = [
        place.title
        for place_slug in route.place_slugs
        if (place := catalog.place_by_slug(place_slug)) is not None
    ]
    stops = "\n".join(f"{index}. {title}" for index, title in enumerate(titles, start=1))

    await callback.message.edit_text(
        f"🧭 <b>{route.title}</b>\n\n"
        f"{route.summary}\n\n"
        f"⏱ ~{route.duration_minutes // 60} ч {route.duration_minutes % 60:02d} мин\n"
        f"🚶 ~{route.distance_km:g} км\n\n"
        f"<b>Точки:</b>\n{stops}\n\n"
        "Карточки точек уже содержат геопозицию; построение единого маршрута по карте "
        "добавим отдельным слоем.",
        reply_markup=back_home_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:excursions")
async def excursions(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "🎟 <b>Экскурсии</b>\n\n"
        "Раздел подготовлен под подключение актуальных предложений. "
        "До подключения источника бот не будет показывать вымышленные цены, "
        "расписания или наличие мест.",
        reply_markup=back_home_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.in_({"menu:favorites", "stub:favorites"}))
async def favorites(callback: CallbackQuery) -> None:
    await callback.answer("Избранное добавим следующим шагом.", show_alert=True)


@router.callback_query(F.data == "menu:search")
async def search(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "🔍 <b>Поиск</b>\n\n"
        "Следующий шаг — поиск по названию, категории и тегам. "
        "После этого добавим свободные запросы вроде «куда сходить вечером».",
        reply_markup=back_home_keyboard(),
    )
    await callback.answer()

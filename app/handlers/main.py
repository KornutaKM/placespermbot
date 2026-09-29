from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from app.data.spb import (
    CATEGORY_LABELS,
    CITY_NAME,
    place_by_slug,
    places_for_category,
    route_by_slug,
)
from app.keyboards import (
    back_home_keyboard,
    categories_keyboard,
    home_keyboard,
    place_keyboard,
    places_keyboard,
    routes_keyboard,
)

router = Router()


def home_text() -> str:
    return (
        f"📍 <b>{CITY_NAME}</b>\n\n"
        "Что хотите сделать?\n\n"
        "Можно выбрать места, готовую прогулку или подборку под настроение."
    )


@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(
        "👋 <b>Добро пожаловать!</b>\n\n"
        "Я — городской гид в Telegram. Первый город проекта — Санкт-Петербург.\n\n"
        + home_text(),
        reply_markup=home_keyboard(),
    )


@router.callback_query(F.data == "menu:home")
async def menu_home(callback: CallbackQuery) -> None:
    await callback.message.edit_text(home_text(), reply_markup=home_keyboard())
    await callback.answer()


@router.callback_query(F.data == "menu:places")
async def menu_places(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "📍 <b>Куда сходить</b>\n\nВыберите тип места:",
        reply_markup=categories_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cat:"))
async def category(callback: CallbackQuery) -> None:
    key = callback.data.split(":", 1)[1]
    places = places_for_category(key)
    label = CATEGORY_LABELS.get(key, "Подборка")

    if not places:
        await callback.answer("Для этой подборки пока нет мест.", show_alert=True)
        return

    await callback.message.edit_text(
        f"<b>{label}</b>\n\n"
        "Выберите место. На первом этапе показываем стабильные описательные данные "
        "без непроверенных цен и расписаний.",
        reply_markup=places_keyboard(tuple(place.slug for place in places)),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("place:"))
async def place_card(callback: CallbackQuery) -> None:
    slug = callback.data.split(":", 1)[1]
    place = place_by_slug(slug)
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
        reply_markup=place_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:routes")
async def menu_routes(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "🗺 <b>Готовые маршруты</b>\n\n"
        "Первый набор прогулок по Петербургу:",
        reply_markup=routes_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("route:"))
async def route_card(callback: CallbackQuery) -> None:
    slug = callback.data.split(":", 1)[1]
    route = route_by_slug(slug)
    if route is None:
        await callback.answer("Маршрут не найден.", show_alert=True)
        return

    titles = [
        place.title
        for place_slug in route.place_slugs
        if (place := place_by_slug(place_slug)) is not None
    ]
    stops = "\n".join(f"{index}. {title}" for index, title in enumerate(titles, start=1))

    await callback.message.edit_text(
        f"🧭 <b>{route.title}</b>\n\n"
        f"{route.summary}\n\n"
        f"⏱ ~{route.duration_minutes // 60} ч {route.duration_minutes % 60:02d} мин\n"
        f"🚶 ~{route.distance_km:g} км\n\n"
        f"<b>Точки:</b>\n{stops}\n\n"
        "Точное построение пути по карте добавим вместе с геоданными.",
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

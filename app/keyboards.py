from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.data.spb import CATEGORY_LABELS, PLACES, ROUTES


def home_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="📍 Куда сходить", callback_data="menu:places"),
            InlineKeyboardButton(text="🗺 Маршруты", callback_data="menu:routes"),
        ],
        [
            InlineKeyboardButton(text="🎟 Экскурсии", callback_data="menu:excursions"),
            InlineKeyboardButton(text="✨ Необычные", callback_data="cat:unusual"),
        ],
        [
            InlineKeyboardButton(text="👨‍👩‍👧 С детьми", callback_data="cat:family"),
            InlineKeyboardButton(text="💸 Бесплатно", callback_data="cat:free"),
        ],
        [
            InlineKeyboardButton(text="❤️ Избранное", callback_data="menu:favorites"),
            InlineKeyboardButton(text="🔍 Поиск", callback_data="menu:search"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def categories_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"cat:{key}")]
        for key, label in CATEGORY_LABELS.items()
    ]
    rows.append([InlineKeyboardButton(text="← Главное меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def places_keyboard(slugs: tuple[str, ...]) -> InlineKeyboardMarkup:
    by_slug = {place.slug: place for place in PLACES}
    rows = [
        [
            InlineKeyboardButton(
                text=f"{by_slug[slug].emoji} {by_slug[slug].title}",
                callback_data=f"place:{slug}",
            )
        ]
        for slug in slugs
        if slug in by_slug
    ]
    rows.append([InlineKeyboardButton(text="← Категории", callback_data="menu:places")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def routes_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"🧭 {route.title}", callback_data=f"route:{route.slug}")]
        for route in ROUTES
    ]
    rows.append([InlineKeyboardButton(text="← Главное меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="← Главное меню", callback_data="menu:home")]
        ]
    )


def place_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗺 Маршруты", callback_data="menu:routes"),
                InlineKeyboardButton(text="❤️ В избранное", callback_data="stub:favorites"),
            ],
            [InlineKeyboardButton(text="← Категории", callback_data="menu:places")],
        ]
    )

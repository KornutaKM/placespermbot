from collections.abc import Mapping

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from app.domain import Place, RoutePlan
from app.excursions import ExcursionProvider
from app.maps import google_maps_route_urls
from app.planner import INTEREST_LABELS


def home_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="📍 Куда сходить", callback_data="menu:places"),
            InlineKeyboardButton(text="🗺 Маршруты", callback_data="menu:routes"),
        ],
        [
            InlineKeyboardButton(text="📡 Рядом со мной", callback_data="menu:nearby"),
        ],
        [
            InlineKeyboardButton(text="🪄 Собрать маршрут", callback_data="builder:start"),
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


def categories_keyboard(category_labels: Mapping[str, str]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"cat:{key}")]
        for key, label in category_labels.items()
    ]
    rows.append([InlineKeyboardButton(text="← Главное меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def places_keyboard(
    places: tuple[Place, ...],
    *,
    back_callback: str = "menu:places",
    back_text: str = "← Категории",
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{place.emoji} {place.title}",
                callback_data=f"place:{place.slug}",
            )
        ]
        for place in places
    ]
    rows.append([InlineKeyboardButton(text=back_text, callback_data=back_callback)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def routes_keyboard(routes: tuple[RoutePlan, ...]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"🧭 {route.title}", callback_data=f"route:{route.slug}")]
        for route in routes
    ]
    rows.append([InlineKeyboardButton(text="← Главное меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def route_duration_keyboard(*, location_selected: bool = False) -> InlineKeyboardMarkup:
    location_text = "✅ Старт: моя геопозиция" if location_selected else "📍 Начать рядом со мной"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="2 часа", callback_data="builder:duration:120"),
                InlineKeyboardButton(text="4 часа", callback_data="builder:duration:240"),
                InlineKeyboardButton(text="6 часов", callback_data="builder:duration:360"),
            ],
            [
                InlineKeyboardButton(
                    text=location_text,
                    callback_data="builder:location",
                )
            ],
            [InlineKeyboardButton(text="← Главное меню", callback_data="menu:home")],
        ]
    )


def request_location_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text="📍 Отправить мою геопозицию",
                    request_location=True,
                )
            ],
            [KeyboardButton(text="Отмена")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Нажмите кнопку, чтобы поделиться геопозицией",
    )


def route_interest_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"builder:interest:{key}")]
        for key, label in INTEREST_LABELS.items()
    ]
    rows.append([InlineKeyboardButton(text="← Главное меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def generated_route_keyboard(places: tuple[Place, ...]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{index}. {place.emoji} {place.title}",
                callback_data=f"place:{place.slug}",
            )
        ]
        for index, place in enumerate(places, start=1)
    ]
    rows.extend(_google_maps_rows(places))
    rows.append([InlineKeyboardButton(text="🪄 Новый маршрут", callback_data="builder:start")])
    rows.append([InlineKeyboardButton(text="← Главное меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def route_details_keyboard(places: tuple[Place, ...]) -> InlineKeyboardMarkup:
    rows = _google_maps_rows(places)
    rows.append([InlineKeyboardButton(text="← Главное меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _google_maps_rows(places: tuple[Place, ...]) -> list[list[InlineKeyboardButton]]:
    urls = google_maps_route_urls(places)
    if not urls:
        return []

    if len(urls) == 1:
        return [
            [
                InlineKeyboardButton(
                    text="🗺 Открыть маршрут в Google Maps",
                    url=urls[0],
                )
            ]
        ]

    return [
        [
            InlineKeyboardButton(
                text=f"🗺 Google Maps · часть {index}/{len(urls)}",
                url=url,
            )
        ]
        for index, url in enumerate(urls, start=1)
    ]


def excursion_providers_keyboard(
    providers: tuple[ExcursionProvider, ...],
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"🎟 Открыть {provider.name}",
                url=provider.catalog_url,
            )
        ]
        for provider in providers
    ]
    rows.append([InlineKeyboardButton(text="← Главное меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="← Главное меню", callback_data="menu:home")]
        ]
    )


def place_keyboard(place_slug: str, *, is_favorite: bool = False) -> InlineKeyboardMarkup:
    favorite_text = "💔 Убрать из избранного" if is_favorite else "❤️ В избранное"
    favorite_action = "remove" if is_favorite else "add"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📍 Показать на карте",
                    callback_data=f"geo:{place_slug}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✨ Что рядом",
                    callback_data=f"nearby:{place_slug}",
                ),
                InlineKeyboardButton(
                    text=favorite_text,
                    callback_data=f"favorite:{favorite_action}:{place_slug}",
                ),
            ],
            [
                InlineKeyboardButton(text="🗺 Маршруты", callback_data="menu:routes"),
                InlineKeyboardButton(text="← Категории", callback_data="menu:places"),
            ],
        ]
    )

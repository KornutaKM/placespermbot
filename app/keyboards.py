from collections.abc import Mapping

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from app.catalog import CityCatalog
from app.domain import Place, RoutePlan
from app.events import EventProvider
from app.excursions import ExcursionProvider
from app.maps import google_maps_directions_to_place_url, google_maps_route_urls
from app.navigation import (
    DEFAULT_CONTEXT,
    back_target,
    favorite_callback,
    nearby_callback,
    personal_context,
    place_callback,
    route_context,
    saved_route_context,
    visited_callback,
    visited_context,
)
from app.pagination import Page
from app.planner import INTEREST_LABELS
from app.saved_routes import SavedRoute


def home_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="🌆 Сменить город", callback_data="menu:cities"),
            InlineKeyboardButton(text="👤 Мой гид", callback_data="menu:profile"),
        ],
        [
            InlineKeyboardButton(text="📍 Куда сходить", callback_data="menu:places"),
            InlineKeyboardButton(text="🗺 Маршруты", callback_data="menu:routes"),
        ],
        [
            InlineKeyboardButton(text="🎯 Для меня", callback_data="menu:personal"),
            InlineKeyboardButton(text="📡 Рядом со мной", callback_data="menu:nearby"),
        ],
        [
            InlineKeyboardButton(text="🪄 Собрать маршрут", callback_data="builder:start"),
        ],
        [
            InlineKeyboardButton(text="🎟 Экскурсии", callback_data="menu:excursions"),
            InlineKeyboardButton(text="🎭 События", callback_data="menu:events"),
        ],
        [
            InlineKeyboardButton(text="✨ Необычные", callback_data="cat:unusual"),
            InlineKeyboardButton(text="👨‍👩‍👧 С детьми", callback_data="cat:family"),
        ],
        [
            InlineKeyboardButton(text="💸 Бесплатно", callback_data="cat:free"),
            InlineKeyboardButton(text="❤️ Избранное", callback_data="menu:favorites"),
        ],
        [
            InlineKeyboardButton(text="✅ Посещённые", callback_data="menu:visited"),
            InlineKeyboardButton(text="🔍 Поиск", callback_data="menu:search"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🌆 Сменить город",
                    callback_data="menu:cities",
                ),
                InlineKeyboardButton(
                    text="🎯 Интересы",
                    callback_data="pref:edit",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❤️ Избранное",
                    callback_data="menu:favorites",
                ),
                InlineKeyboardButton(
                    text="✅ Посещённые",
                    callback_data="menu:visited",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🧭 Сохранённые маршруты",
                    callback_data="menu:savedroutes",
                ),
                InlineKeyboardButton(
                    text="📦 Экспорт данных",
                    callback_data="profile:export",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="← Главное меню",
                    callback_data="menu:home",
                )
            ],
        ]
    )


def cities_keyboard(
    catalogs: tuple[CityCatalog, ...],
    current_slug: str,
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=("✅ " if catalog.slug == current_slug else "") + catalog.name,
                callback_data=f"city:set:{catalog.slug}",
            )
        ]
        for catalog in catalogs
    ]
    rows.append([InlineKeyboardButton(text="← Главное меню", callback_data="menu:home")])
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
    place_context: str = DEFAULT_CONTEXT,
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{place.emoji} {place.title}",
                callback_data=place_callback(place.slug, place_context),
            )
        ]
        for place in places
    ]
    rows.append([InlineKeyboardButton(text=back_text, callback_data=back_callback)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def paginated_places_keyboard(
    page: Page[Place],
    *,
    page_callback_prefix: str,
    back_callback: str,
    back_text: str,
    place_context: str = DEFAULT_CONTEXT,
    extra_rows: list[list[InlineKeyboardButton]] | None = None,
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{place.emoji} {place.title}",
                callback_data=place_callback(place.slug, place_context),
            )
        ]
        for place in page.items
    ]

    navigation: list[InlineKeyboardButton] = []
    if page.index > 0:
        navigation.append(
            InlineKeyboardButton(
                text="←",
                callback_data=f"{page_callback_prefix}:{page.index - 1}",
            )
        )

    navigation.append(
        InlineKeyboardButton(
            text=f"{page.number}/{page.total_pages}",
            callback_data="noop",
        )
    )

    if page.index + 1 < page.total_pages:
        navigation.append(
            InlineKeyboardButton(
                text="→",
                callback_data=f"{page_callback_prefix}:{page.index + 1}",
            )
        )

    if page.total_pages > 1:
        rows.append(navigation)

    if extra_rows:
        rows.extend(extra_rows)

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


def generated_route_keyboard(
    places: tuple[Place, ...],
    *,
    save_callback: str | None = None,
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{index}. {place.emoji} {place.title}",
                callback_data=place_callback(place.slug, route_context()),
            )
        ]
        for index, place in enumerate(places, start=1)
    ]
    rows.extend(_google_maps_rows(places))
    if save_callback is not None:
        rows.append(
            [
                InlineKeyboardButton(
                    text="💾 Сохранить маршрут",
                    callback_data=save_callback,
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="🪄 Новый маршрут", callback_data="builder:start")])
    rows.append([InlineKeyboardButton(text="← Главное меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def saved_routes_keyboard(page: Page[SavedRoute]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=(
                    f"{INTEREST_LABELS.get(route.interest, route.interest)}"
                    f" · {route.budget_minutes // 60} ч"
                ),
                callback_data=f"savedroute:{route.route_id}",
            )
        ]
        for route in page.items
    ]

    navigation: list[InlineKeyboardButton] = []
    if page.index > 0:
        navigation.append(
            InlineKeyboardButton(
                text="←",
                callback_data=f"savedroutes:{page.index - 1}",
            )
        )
    navigation.append(
        InlineKeyboardButton(
            text=f"{page.number}/{page.total_pages}",
            callback_data="noop",
        )
    )
    if page.index + 1 < page.total_pages:
        navigation.append(
            InlineKeyboardButton(
                text="→",
                callback_data=f"savedroutes:{page.index + 1}",
            )
        )
    if page.total_pages > 1:
        rows.append(navigation)

    rows.append(
        [InlineKeyboardButton(text="← Мой гид", callback_data="menu:profile")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def saved_route_details_keyboard(
    route: SavedRoute,
    places: tuple[Place, ...],
) -> InlineKeyboardMarkup:
    context = saved_route_context(route.route_id)
    rows = [
        [
            InlineKeyboardButton(
                text=f"{index}. {place.emoji} {place.title}",
                callback_data=place_callback(place.slug, context),
            )
        ]
        for index, place in enumerate(places, start=1)
    ]
    rows.extend(_google_maps_rows(places))
    rows.append(
        [
            InlineKeyboardButton(
                text="🗑 Удалить маршрут",
                callback_data=f"savedroute:delete:{route.route_id}",
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text="← Сохранённые маршруты",
                callback_data="menu:savedroutes",
            )
        ]
    )
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


def event_providers_keyboard(
    providers: tuple[EventProvider, ...],
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"🎭 Открыть {provider.name}",
                url=provider.catalog_url,
            )
        ]
        for provider in providers
    ]
    rows.append([InlineKeyboardButton(text="← Главное меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def interests_keyboard(selected: tuple[str, ...]) -> InlineKeyboardMarkup:
    selected_set = set(selected)
    rows = [
        [
            InlineKeyboardButton(
                text=("✅ " if key in selected_set else "▫️ ") + label,
                callback_data=f"pref:toggle:{key}",
            )
        ]
        for key, label in INTEREST_LABELS.items()
    ]
    rows.append([InlineKeyboardButton(text="Готово", callback_data="pref:done")])
    rows.append([InlineKeyboardButton(text="← Главное меню", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def personalized_places_keyboard(
    page: Page[Place],
) -> InlineKeyboardMarkup:
    return paginated_places_keyboard(
        page,
        page_callback_prefix="personalpage",
        back_callback="menu:home",
        back_text="← Главное меню",
        place_context=personal_context(page.index),
        extra_rows=[
            [
                InlineKeyboardButton(
                    text="⚙️ Изменить интересы",
                    callback_data="pref:edit",
                )
            ]
        ],
    )


def visited_places_keyboard(page: Page[Place]) -> InlineKeyboardMarkup:
    return paginated_places_keyboard(
        page,
        page_callback_prefix="visitedpage",
        back_callback="menu:home",
        back_text="← Главное меню",
        place_context=visited_context(page.index),
    )


def back_home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="← Главное меню", callback_data="menu:home")]
        ]
    )


def place_keyboard(
    place: Place,
    *,
    is_favorite: bool = False,
    is_visited: bool = False,
    context: str = DEFAULT_CONTEXT,
) -> InlineKeyboardMarkup:
    favorite_text = "💔 Убрать из избранного" if is_favorite else "❤️ В избранное"
    favorite_action = "remove" if is_favorite else "add"
    visited_text = "↩️ Убрать «был»" if is_visited else "✅ Уже был"
    visited_action = "remove" if is_visited else "add"
    back = back_target(context)

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📍 Показать на карте",
                    callback_data=f"geo:{place.slug}",
                ),
                InlineKeyboardButton(
                    text="🚶 Маршрут сюда",
                    url=google_maps_directions_to_place_url(place),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="✨ Что рядом",
                    callback_data=nearby_callback(place.slug, context),
                ),
                InlineKeyboardButton(
                    text=favorite_text,
                    callback_data=favorite_callback(
                        favorite_action,
                        place.slug,
                        context,
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    text=visited_text,
                    callback_data=visited_callback(
                        visited_action,
                        place.slug,
                        context,
                    ),
                )
            ],
            [
                InlineKeyboardButton(text="🗺 Маршруты", callback_data="menu:routes"),
                InlineKeyboardButton(text=back.text, callback_data=back.callback_data),
            ],
        ]
    )

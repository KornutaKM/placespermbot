from __future__ import annotations

from dataclasses import dataclass

TELEGRAM_CALLBACK_MAX_BYTES = 64
DEFAULT_CONTEXT = "d"


@dataclass(frozen=True, slots=True)
class BackTarget:
    callback_data: str
    text: str


def place_callback(place_slug: str, context: str = DEFAULT_CONTEXT) -> str:
    return _bounded_callback(f"place:{place_slug}|{normalize_context(context)}")


def favorite_callback(action: str, place_slug: str, context: str) -> str:
    if action not in {"add", "remove"}:
        raise ValueError("unsupported favorite action")
    return _bounded_callback(
        f"favorite:{action}:{place_slug}|{normalize_context(context)}"
    )


def nearby_callback(place_slug: str, context: str) -> str:
    return _bounded_callback(f"nearby:{place_slug}|{normalize_context(context)}")


def similar_callback(place_slug: str, context: str) -> str:
    return _bounded_callback(
        f"similar:{place_slug}|{normalize_context(context)}"
    )


def place_route_callback(place_slug: str, context: str) -> str:
    return _bounded_callback(
        f"proute:{place_slug}|{normalize_context(context)}"
    )


def place_route_duration_callback(
    budget_minutes: int,
    place_slug: str,
    context: str,
) -> str:
    if budget_minutes not in {120, 240, 360}:
        raise ValueError("unsupported place-route budget")
    return _bounded_callback(
        f"prouted:{budget_minutes // 60}:{place_slug}|"
        f"{normalize_context(context)}"
    )


def dismissed_callback(action: str, place_slug: str, context: str) -> str:
    if action not in {"add", "remove"}:
        raise ValueError("unsupported dismissed action")
    return _bounded_callback(
        f"dismiss:{action}:{place_slug}|{normalize_context(context)}"
    )


def visited_callback(action: str, place_slug: str, context: str) -> str:
    if action not in {"add", "remove"}:
        raise ValueError("unsupported visited action")
    return _bounded_callback(
        f"visit:{action}:{place_slug}|{normalize_context(context)}"
    )


def parse_place_callback(data: str) -> tuple[str, str]:
    if not data.startswith("place:"):
        raise ValueError("not a place callback")
    return _parse_slug_context(data.removeprefix("place:"))


def parse_favorite_callback(data: str) -> tuple[str, str, str]:
    if not data.startswith("favorite:"):
        raise ValueError("not a favorite callback")

    payload = data.removeprefix("favorite:")
    action, separator, remainder = payload.partition(":")
    if not separator or action not in {"add", "remove"}:
        raise ValueError("invalid favorite callback")

    slug, context = _parse_slug_context(remainder)
    return action, slug, context


def parse_nearby_callback(data: str) -> tuple[str, str]:
    if not data.startswith("nearby:"):
        raise ValueError("not a nearby callback")
    return _parse_slug_context(data.removeprefix("nearby:"))


def parse_similar_callback(data: str) -> tuple[str, str]:
    if not data.startswith("similar:"):
        raise ValueError("not a similar callback")
    return _parse_slug_context(data.removeprefix("similar:"))


def parse_place_route_callback(data: str) -> tuple[str, str]:
    if not data.startswith("proute:"):
        raise ValueError("not a place-route callback")
    return _parse_slug_context(data.removeprefix("proute:"))


def parse_place_route_duration_callback(
    data: str,
) -> tuple[int, str, str]:
    if not data.startswith("prouted:"):
        raise ValueError("not a place-route duration callback")

    payload = data.removeprefix("prouted:")
    raw_hours, separator, remainder = payload.partition(":")
    if not separator:
        raise ValueError("invalid place-route duration callback")

    try:
        budget_minutes = int(raw_hours) * 60
    except ValueError as exc:
        raise ValueError("invalid place-route duration") from exc

    if budget_minutes not in {120, 240, 360}:
        raise ValueError("unsupported place-route budget")

    place_slug, context = _parse_slug_context(remainder)
    return budget_minutes, place_slug, context


def parse_dismissed_callback(data: str) -> tuple[str, str, str]:
    if not data.startswith("dismiss:"):
        raise ValueError("not a dismissed callback")

    payload = data.removeprefix("dismiss:")
    action, separator, remainder = payload.partition(":")
    if not separator or action not in {"add", "remove"}:
        raise ValueError("invalid dismissed callback")

    slug, context = _parse_slug_context(remainder)
    return action, slug, context


def parse_visited_callback(data: str) -> tuple[str, str, str]:
    if not data.startswith("visit:"):
        raise ValueError("not a visited callback")

    payload = data.removeprefix("visit:")
    action, separator, remainder = payload.partition(":")
    if not separator or action not in {"add", "remove"}:
        raise ValueError("invalid visited callback")

    slug, context = _parse_slug_context(remainder)
    return action, slug, context


def category_context(category_key: str, page_index: int) -> str:
    return normalize_context(f"c.{category_key}.{max(page_index, 0)}")


def favorites_context(page_index: int) -> str:
    return normalize_context(f"f.{max(page_index, 0)}")


def personal_context(page_index: int) -> str:
    return normalize_context(f"p.{max(page_index, 0)}")


def dismissed_context(page_index: int) -> str:
    return normalize_context(f"x.{max(page_index, 0)}")


def visited_context(page_index: int) -> str:
    return normalize_context(f"v.{max(page_index, 0)}")


def route_context() -> str:
    return "r"


def saved_route_context(route_id: str) -> str:
    clean = route_id.strip()
    if not clean or not clean.isalnum() or len(clean) > 20:
        return DEFAULT_CONTEXT
    return normalize_context(f"z.{clean}")


def search_context() -> str:
    return "s"


def home_context() -> str:
    return "h"


def nearby_child_context(origin_slug: str, parent_context: str) -> str:
    parent = normalize_context(parent_context)
    context = f"n.{origin_slug}@{parent}"
    return normalize_context(context)


def similar_child_context(origin_slug: str, parent_context: str) -> str:
    parent = normalize_context(parent_context)
    context = f"m.{origin_slug}@{parent}"
    return normalize_context(context)


def back_target(context: str) -> BackTarget:
    normalized = normalize_context(context)

    if normalized.startswith("c."):
        parts = normalized.split(".")
        if len(parts) == 3 and parts[2].isdigit():
            return BackTarget(
                callback_data=f"catpage:{parts[1]}:{parts[2]}",
                text="← К подборке",
            )

    if normalized.startswith("f."):
        page = normalized.removeprefix("f.")
        if page.isdigit():
            return BackTarget(
                callback_data=f"favpage:{page}",
                text="← Избранное",
            )

    if normalized.startswith("p."):
        page = normalized.removeprefix("p.")
        if page.isdigit():
            return BackTarget(
                callback_data=f"personalpage:{page}",
                text="← Для меня",
            )

    if normalized.startswith("v."):
        page = normalized.removeprefix("v.")
        if page.isdigit():
            return BackTarget(
                callback_data=f"visitedpage:{page}",
                text="← Посещённые",
            )

    if normalized.startswith("x."):
        page = normalized.removeprefix("x.")
        if page.isdigit():
            return BackTarget(
                callback_data=f"dismissedpage:{page}",
                text="← Скрытые рекомендации",
            )

    if normalized.startswith("n."):
        payload = normalized.removeprefix("n.")
        origin_slug, separator, parent = payload.partition("@")
        if origin_slug:
            return BackTarget(
                callback_data=place_callback(
                    origin_slug,
                    parent if separator else DEFAULT_CONTEXT,
                ),
                text="← К исходному месту",
            )

    if normalized.startswith("m."):
        payload = normalized.removeprefix("m.")
        origin_slug, separator, parent = payload.partition("@")
        if origin_slug:
            return BackTarget(
                callback_data=place_callback(
                    origin_slug,
                    parent if separator else DEFAULT_CONTEXT,
                ),
                text="← К исходному месту",
            )

    if normalized.startswith("z."):
        route_id = normalized.removeprefix("z.")
        if route_id and route_id.isalnum():
            return BackTarget(
                callback_data=f"savedroute:{route_id}",
                text="← Сохранённый маршрут",
            )

    if normalized == "r":
        return BackTarget(callback_data="menu:routes", text="← Маршруты")

    if normalized == "s":
        return BackTarget(callback_data="menu:search", text="← Новый поиск")

    if normalized == "h":
        return BackTarget(callback_data="menu:home", text="← Главное меню")

    return BackTarget(callback_data="menu:places", text="← Категории")


def normalize_context(context: str) -> str:
    value = context.strip()
    if not value:
        return DEFAULT_CONTEXT

    if "|" in value or ":" in value:
        return DEFAULT_CONTEXT

    if len(value.encode("utf-8")) > 40:
        return DEFAULT_CONTEXT

    return value


def _parse_slug_context(payload: str) -> tuple[str, str]:
    slug, separator, context = payload.partition("|")
    slug = slug.strip()
    if not slug:
        raise ValueError("missing place slug")

    return slug, normalize_context(context if separator else DEFAULT_CONTEXT)


def _bounded_callback(value: str) -> str:
    if len(value.encode("utf-8")) > TELEGRAM_CALLBACK_MAX_BYTES:
        raise ValueError("callback_data exceeds Telegram 64-byte limit")
    return value

from app.personal_route import PersonalRouteResult
from app.recommendations import recommendation_reason_text
from app.saved_routes import PERSONAL_ROUTE_LABEL


def personal_route_result_text(
    result: PersonalRouteResult,
    *,
    location_used: bool,
) -> str:
    route = result.route
    stops = "\n".join(
        _stop_text(index, place.slug, result)
        for index, place in enumerate(route.places, start=1)
    )
    hours, minutes = divmod(route.estimated_minutes, 60)
    start_line = "Старт: от вашей геопозиции\n" if location_used else ""

    return (
        f"🪄 <b>{PERSONAL_ROUTE_LABEL}</b>\n\n"
        f"Бюджет: {route.budget_minutes // 60} ч\n"
        f"{start_line}"
        f"Оценка маршрута: ~{hours} ч {minutes:02d} мин\n"
        f"Пешком по расчёту: ~{route.distance_km:g} км\n"
        f"Точек: {len(route.places)}\n\n"
        f"<b>Маршрут:</b>\n{stops}\n\n"
        "Использованы текущие интересы, избранное, история посещений "
        "и пройденных маршрутов; уже посещённые, пройденные и отмеченные "
        "«Не интересно» места исключены. "
        "Геопозиция после расчёта не сохраняется."
    )


def _stop_text(index: int, place_slug: str, result: PersonalRouteResult) -> str:
    place = next(place for place in result.route.places if place.slug == place_slug)
    recommendation = result.recommendation_for(place_slug)
    base = f"{index}. {place.emoji} {place.title} — ~{place.visit_minutes} мин"
    if recommendation is None:
        return base
    reason = recommendation_reason_text(recommendation)
    return f"{base}\n   ↳ {reason}" if reason else base

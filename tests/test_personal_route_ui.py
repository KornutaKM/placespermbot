from app.catalog import get_catalog
from app.data.spb import CITY_SLUG
from app.personal_route import build_explained_personal_route
from app.personal_route_ui import personal_route_result_text


def catalog():
    return get_catalog(CITY_SLUG)


def test_personal_route_text_explains_each_selected_stop() -> None:
    result = build_explained_personal_route(
        catalog(),
        ("museums",),
        budget_minutes=240,
    )
    assert result is not None

    text = personal_route_result_text(result, location_used=False)

    assert "<b>Маршрут:</b>" in text
    assert "Старт: от вашей геопозиции" not in text
    assert text.count("↳ интерес: 🖼 Музеи") == len(result.route.places)
    for place in result.route.places:
        assert place.title in text


def test_personal_route_text_marks_ephemeral_location_usage() -> None:
    result = build_explained_personal_route(
        catalog(),
        ("classic",),
        budget_minutes=180,
    )
    assert result is not None

    text = personal_route_result_text(result, location_used=True)

    assert "Старт: от вашей геопозиции" in text
    assert "Геопозиция после расчёта не сохраняется." in text


def test_personal_route_text_stays_within_telegram_message_limit() -> None:
    result = build_explained_personal_route(
        catalog(),
        ("classic", "museums", "architecture", "walks", "unusual", "family", "free"),
        budget_minutes=480,
    )
    assert result is not None

    text = personal_route_result_text(result, location_used=True)

    assert len(text) <= 4096

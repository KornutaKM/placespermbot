from html import escape

from app.catalog import CityCatalog


def search_prompt(catalog: CityCatalog) -> str:
    example = (
        escape(catalog.places[0].title)
        if catalog.places
        else "название места"
    )
    return (
        "🔍 <b>Поиск по местам</b>\n\n"
        "Напишите название, тип места, район или интерес.\n\n"
        f"Например: <i>{example}</i>, <i>музей</i>, "
        "<i>парк</i>, <i>архитектура</i>."
    )


def search_not_found_text(query: str) -> str:
    return (
        f"🔍 По запросу <b>{escape(query)}</b> ничего не нашлось.\n\n"
        "Попробуйте название места, «музей», «парк», «архитектура» или район."
    )


def search_results_text(query: str, result_count: int) -> str:
    if result_count < 0:
        raise ValueError("result_count must not be negative")

    return (
        f"🔍 <b>Результаты поиска: {escape(query)}</b>\n\n"
        f"Найдено: {result_count}. Выберите место:"
    )

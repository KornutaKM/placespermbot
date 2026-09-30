import pytest

from app.catalog import get_catalog
from app.search_ui import (
    search_not_found_text,
    search_prompt,
    search_results_text,
)


def test_search_prompt_uses_active_city_catalog_example() -> None:
    spb = get_catalog("saint-petersburg")
    perm = get_catalog("perm")

    spb_text = search_prompt(spb)
    perm_text = search_prompt(perm)

    assert spb.places[0].title in spb_text
    assert perm.places[0].title in perm_text
    assert "Эрмитаж" not in perm_text
    assert "музей" in perm_text
    assert "парк" in perm_text
    assert "архитектура" in perm_text


@pytest.mark.parametrize(
    "query",
    (
        "<b>Эрмитаж</b>",
        "музей & парк",
        "<script>alert(1)</script>",
        '"><i>сломать</i>',
    ),
)
def test_search_output_escapes_user_query_for_telegram_html(query: str) -> None:
    not_found = search_not_found_text(query)
    results = search_results_text(query, 3)

    for body in (not_found, results):
        assert query not in body
        assert "&lt;" in body or "&amp;" in body or "&quot;" in body


def test_search_result_count_must_not_be_negative() -> None:
    with pytest.raises(ValueError, match="result_count"):
        search_results_text("музей", -1)


def test_search_copy_does_not_mutate_query_used_for_matching() -> None:
    catalog = get_catalog("perm")
    query = "<b>медведь</b>"

    search_not_found_text(query)
    search_results_text(query, 0)

    assert catalog.search_places(query) == ()
    assert query == "<b>медведь</b>"

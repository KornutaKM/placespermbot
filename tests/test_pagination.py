import pytest

from app.pagination import PAGE_SIZE, paginate


def test_first_page_is_bounded() -> None:
    items = tuple(range(20))
    page = paginate(items, 0)

    assert page.items == tuple(range(PAGE_SIZE))
    assert len(page.items) == PAGE_SIZE
    assert page.index == 0
    assert page.number == 1
    assert page.total_pages == 4
    assert page.total_items == 20


def test_last_page_contains_remainder() -> None:
    items = tuple(range(20))
    page = paginate(items, 3)

    assert page.items == (18, 19)
    assert page.number == 4
    assert page.total_pages == 4


def test_negative_page_is_normalized_to_first() -> None:
    page = paginate(tuple(range(10)), -50)

    assert page.index == 0
    assert page.items == tuple(range(PAGE_SIZE))


def test_too_large_page_is_normalized_to_last() -> None:
    page = paginate(tuple(range(10)), 500)

    assert page.index == 1
    assert page.items == (6, 7, 8, 9)


def test_empty_collection_has_single_empty_page() -> None:
    page = paginate((), 0)

    assert page.items == ()
    assert page.number == 1
    assert page.total_pages == 1
    assert page.total_items == 0


def test_invalid_page_size_fails_closed() -> None:
    with pytest.raises(ValueError, match="page_size"):
        paginate((1, 2, 3), 0, page_size=0)

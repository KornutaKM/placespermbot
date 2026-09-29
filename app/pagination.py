from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")

PAGE_SIZE = 6


@dataclass(frozen=True, slots=True)
class Page(Generic[T]):
    items: tuple[T, ...]
    index: int
    total_pages: int
    total_items: int

    @property
    def number(self) -> int:
        return self.index + 1


def paginate(
    items: tuple[T, ...],
    page: int,
    *,
    page_size: int = PAGE_SIZE,
) -> Page[T]:
    if page_size <= 0:
        raise ValueError("page_size must be positive")

    total_items = len(items)
    total_pages = max(1, (total_items + page_size - 1) // page_size)
    normalized = min(max(page, 0), total_pages - 1)
    start = normalized * page_size
    end = start + page_size

    return Page(
        items=items[start:end],
        index=normalized,
        total_pages=total_pages,
        total_items=total_items,
    )

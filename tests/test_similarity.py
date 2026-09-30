from app.catalog import get_catalog
from app.similarity import find_similar_places


def by_slug(results, slug: str):
    return next(
        item
        for item in results
        if item.place.slug == slug
    )


def test_origin_is_never_returned() -> None:
    results = find_similar_places(
        get_catalog("saint-petersburg"),
        "hermitage",
        limit=20,
    )

    assert results
    assert "hermitage" not in {
        item.place.slug
        for item in results
    }


def test_shared_category_and_meaningful_tags_raise_similarity() -> None:
    results = find_similar_places(
        get_catalog("saint-petersburg"),
        "hermitage",
        limit=20,
    )
    russian = by_slug(results, "russian-museum")

    assert russian.score >= 7
    assert "та же категория" in russian.reasons
    assert "общие темы: искусство, музей" in russian.reasons


def test_generic_center_tag_does_not_create_false_similarity() -> None:
    results = find_similar_places(
        get_catalog("saint-petersburg"),
        "palace-square",
        limit=50,
    )

    assert "field-of-mars" not in {
        item.place.slug
        for item in results
    }


def test_similarity_is_deterministic_and_limited() -> None:
    catalog = get_catalog("perm")

    first = find_similar_places(catalog, "perm-bear", limit=5)
    second = find_similar_places(catalog, "perm-bear", limit=5)

    assert first == second
    assert len(first) <= 5


def test_unknown_origin_and_non_positive_limit_fail_closed() -> None:
    catalog = get_catalog("perm")

    assert find_similar_places(catalog, "missing-place") == ()
    assert find_similar_places(catalog, "perm-bear", limit=0) == ()

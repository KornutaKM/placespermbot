import pytest

from app.catalog import get_catalog
from app.data.spb import CITY_SLUG
from app.recommendations import recommend_personalized, recommend_places


def catalog():
    return get_catalog(CITY_SLUG)


def test_empty_interests_return_no_recommendations() -> None:
    assert recommend_places(catalog(), ()) == ()


def test_museum_interest_prefers_museums() -> None:
    places = recommend_places(catalog(), ("museums",))

    assert places
    assert all(place.category == "museums" for place in places)


def test_free_interest_returns_only_free_places() -> None:
    places = recommend_places(catalog(), ("free",))

    assert places
    assert all(place.is_free for place in places)


def test_combined_interests_are_deterministic() -> None:
    interests = ("walks", "family", "free")

    first = recommend_places(catalog(), interests)
    second = recommend_places(catalog(), interests)

    assert first == second
    assert first


def test_combined_interests_can_boost_multi_match_places() -> None:
    places = recommend_places(catalog(), ("walks", "family", "free"))

    assert places
    assert places[0].slug in {"summer-garden", "new-holland"}


def test_limit_is_respected() -> None:
    places = recommend_places(
        catalog(),
        ("classic", "architecture", "free"),
        limit=3,
    )

    assert len(places) <= 3


def test_unknown_interest_fails_closed() -> None:
    with pytest.raises(ValueError, match="Unsupported interests"):
        recommend_places(catalog(), ("nightlife",))


def test_excluded_places_are_not_recommended() -> None:
    baseline = recommend_places(
        catalog(),
        ("museums",),
        limit=20,
    )
    assert baseline

    excluded = {baseline[0].slug}
    filtered = recommend_places(
        catalog(),
        ("museums",),
        limit=20,
        exclude_slugs=excluded,
    )

    assert all(place.slug not in excluded for place in filtered)
    assert len(filtered) == len(baseline) - 1


def test_exclusions_are_applied_before_limit() -> None:
    baseline = recommend_places(
        catalog(),
        ("classic", "architecture", "free"),
        limit=3,
    )
    assert len(baseline) == 3

    filtered = recommend_places(
        catalog(),
        ("classic", "architecture", "free"),
        limit=3,
        exclude_slugs={baseline[0].slug},
    )

    assert len(filtered) == 3
    assert baseline[0].slug not in {place.slug for place in filtered}



def test_personalized_recommendations_explain_single_interest() -> None:
    recommendations = recommend_personalized(
        catalog(),
        ("museums",),
        limit=20,
    )

    assert recommendations
    assert all(item.score > 0 for item in recommendations)
    assert all(
        item.reasons == ("интерес: 🖼 Музеи",)
        for item in recommendations
    )


def test_favorite_gets_small_deterministic_boost() -> None:
    baseline = recommend_personalized(
        catalog(),
        ("museums",),
        limit=20,
    )
    assert len(baseline) >= 2

    later = baseline[1].place.slug
    boosted = recommend_personalized(
        catalog(),
        ("museums",),
        limit=20,
        favorite_slugs={later},
    )

    assert boosted[0].place.slug == later
    assert boosted[0].score == baseline[1].score + 1
    assert "уже в избранном" in boosted[0].reasons


def test_multi_interest_match_gets_bonus_and_reason() -> None:
    recommendations = recommend_personalized(
        catalog(),
        ("walks", "family", "free"),
        limit=20,
    )

    assert recommendations
    first = recommendations[0]
    assert len(first.reasons) >= 1
    assert first.reasons[0].startswith("несколько интересов:")
    assert first.place.slug in {"summer-garden", "new-holland"}


def test_personalized_exclusions_are_applied_before_limit() -> None:
    baseline = recommend_personalized(
        catalog(),
        ("classic", "architecture", "free"),
        limit=3,
    )
    assert len(baseline) == 3

    filtered = recommend_personalized(
        catalog(),
        ("classic", "architecture", "free"),
        limit=3,
        exclude_slugs={baseline[0].place.slug},
    )

    assert len(filtered) == 3
    assert baseline[0].place.slug not in {
        item.place.slug
        for item in filtered
    }


def test_personalized_recommendations_are_deterministic() -> None:
    kwargs = {
        "favorite_slugs": {"summer-garden", "new-holland"},
        "exclude_slugs": {"palace-square"},
    }
    first = recommend_personalized(
        catalog(),
        ("walks", "family", "free"),
        limit=20,
        **kwargs,
    )
    second = recommend_personalized(
        catalog(),
        ("walks", "family", "free"),
        limit=20,
        **kwargs,
    )

    assert first == second


def test_personalized_unknown_interest_fails_closed() -> None:
    with pytest.raises(ValueError, match="Unsupported interests"):
        recommend_personalized(
            catalog(),
            ("nightlife",),
        )



def test_excluded_favorite_cannot_return_to_personalized_results() -> None:
    baseline = recommend_personalized(
        catalog(),
        ("museums",),
        limit=20,
    )
    assert baseline

    dismissed_slug = baseline[0].place.slug
    filtered = recommend_personalized(
        catalog(),
        ("museums",),
        limit=20,
        favorite_slugs={dismissed_slug},
        exclude_slugs={dismissed_slug},
    )

    assert dismissed_slug not in {
        item.place.slug
        for item in filtered
    }



def _recommendation_by_slug(recommendations, slug: str):
    return next(
        item
        for item in recommendations
        if item.place.slug == slug
    )


def test_favorite_affinity_boosts_similar_place_with_concrete_tags() -> None:
    baseline = recommend_personalized(
        catalog(),
        ("museums",),
        limit=50,
    )
    with_favorite = recommend_personalized(
        catalog(),
        ("museums",),
        limit=50,
        favorite_slugs={"hermitage"},
    )

    baseline_russian = _recommendation_by_slug(baseline, "russian-museum")
    affinity_russian = _recommendation_by_slug(with_favorite, "russian-museum")

    assert affinity_russian.score == baseline_russian.score + 2
    assert "похоже на избранное: искусство, музей" in affinity_russian.reasons


def test_exact_favorite_does_not_gain_self_similarity() -> None:
    baseline = recommend_personalized(
        catalog(),
        ("museums",),
        limit=50,
    )
    with_favorite = recommend_personalized(
        catalog(),
        ("museums",),
        limit=50,
        favorite_slugs={"hermitage"},
    )

    baseline_hermitage = _recommendation_by_slug(baseline, "hermitage")
    favorite_hermitage = _recommendation_by_slug(with_favorite, "hermitage")

    assert favorite_hermitage.score == baseline_hermitage.score + 1
    assert "уже в избранном" in favorite_hermitage.reasons
    assert not any(
        reason.startswith("похоже на избранное:")
        for reason in favorite_hermitage.reasons
    )


def test_unrelated_or_foreign_favorite_slug_has_no_affinity_effect() -> None:
    baseline = recommend_personalized(
        catalog(),
        ("museums",),
        limit=50,
    )
    with_foreign_slug = recommend_personalized(
        catalog(),
        ("museums",),
        limit=50,
        favorite_slugs={"perm-bear"},
    )

    assert with_foreign_slug == baseline


def test_service_tags_do_not_create_false_favorite_affinity() -> None:
    baseline = recommend_personalized(
        catalog(),
        ("free",),
        limit=50,
    )
    with_favorite = recommend_personalized(
        catalog(),
        ("free",),
        limit=50,
        favorite_slugs={"palace-square"},
    )

    baseline_field = _recommendation_by_slug(baseline, "field-of-mars")
    favorite_field = _recommendation_by_slug(with_favorite, "field-of-mars")

    assert favorite_field.score == baseline_field.score
    assert not any(
        reason.startswith("похоже на избранное:")
        for reason in favorite_field.reasons
    )


def test_exclusion_overrides_favorite_affinity() -> None:
    filtered = recommend_personalized(
        catalog(),
        ("museums",),
        limit=50,
        favorite_slugs={"hermitage"},
        exclude_slugs={"russian-museum"},
    )

    assert "russian-museum" not in {
        item.place.slug
        for item in filtered
    }

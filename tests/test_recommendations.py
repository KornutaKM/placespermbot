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

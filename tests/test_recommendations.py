import pytest

from app.catalog import get_catalog
from app.data.spb import CITY_SLUG
from app.recommendations import recommend_places


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

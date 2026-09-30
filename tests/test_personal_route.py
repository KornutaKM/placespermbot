from app.catalog import get_catalog
from app.data.spb import CITY_SLUG
from app.planner import build_ranked_route
from app.recommendations import recommend_personalized
from app.saved_routes import PERSONAL_ROUTE_INTEREST


def catalog():
    return get_catalog(CITY_SLUG)


def test_personal_route_uses_ranked_candidates_and_excludes_explicit_signals() -> None:
    city = catalog()
    excluded = {"palace-square", "summer-garden"}
    recommendations = recommend_personalized(
        city,
        ("classic", "architecture", "free"),
        limit=len(city.places),
        favorite_slugs={"kazan-cathedral"},
        exclude_slugs=excluded,
    )

    assert recommendations
    route = build_ranked_route(
        tuple(item.place for item in recommendations),
        budget_minutes=240,
        route_interest=PERSONAL_ROUTE_INTEREST,
    )

    assert route is not None
    assert route.interest == PERSONAL_ROUTE_INTEREST
    assert route.estimated_minutes <= route.budget_minutes
    assert route.places[0].slug == recommendations[0].place.slug
    assert excluded.isdisjoint(place.slug for place in route.places)


def test_personal_route_is_deterministic_for_same_explicit_signals() -> None:
    city = catalog()
    recommendations = recommend_personalized(
        city,
        ("walks", "family", "free"),
        limit=len(city.places),
        favorite_slugs={"new-holland"},
        exclude_slugs={"summer-garden"},
    )
    candidates = tuple(item.place for item in recommendations)

    first = build_ranked_route(
        candidates,
        budget_minutes=360,
        route_interest=PERSONAL_ROUTE_INTEREST,
    )
    second = build_ranked_route(
        candidates,
        budget_minutes=360,
        route_interest=PERSONAL_ROUTE_INTEREST,
    )

    assert first == second

from app.catalog import get_catalog
from app.data.spb import CITY_SLUG
from app.personal_route import (
    build_explained_personal_route,
    build_personal_route,
)
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



def test_personal_route_location_origin_prefers_nearby_ranked_candidate() -> None:
    city = catalog()
    sevkabel = city.place_by_slug("sevkabel-port")
    assert sevkabel is not None

    without_location = build_personal_route(
        city,
        ("unusual",),
        budget_minutes=120,
    )
    with_location = build_personal_route(
        city,
        ("unusual",),
        budget_minutes=120,
        start_latitude=sevkabel.latitude,
        start_longitude=sevkabel.longitude,
    )

    assert without_location is not None
    assert with_location is not None
    assert without_location.places[0].slug == "new-holland"
    assert with_location.places[0].slug == "sevkabel-port"


def test_personal_route_origin_walk_counts_toward_budget_and_distance() -> None:
    route = build_personal_route(
        catalog(),
        ("unusual",),
        budget_minutes=120,
        start_latitude=59.9200,
        start_longitude=30.2300,
    )

    assert route is not None
    assert route.places[0].slug == "sevkabel-port"
    assert route.distance_km > 0
    assert route.estimated_minutes > route.places[0].visit_minutes
    assert route.estimated_minutes <= route.budget_minutes


def test_personal_route_far_origin_fails_closed() -> None:
    route = build_personal_route(
        catalog(),
        ("classic",),
        budget_minutes=120,
        start_latitude=55.7558,
        start_longitude=37.6176,
    )

    assert route is None


def test_personal_route_location_keeps_explicit_exclusions() -> None:
    city = catalog()
    sevkabel = city.place_by_slug("sevkabel-port")
    assert sevkabel is not None

    route = build_personal_route(
        city,
        ("unusual",),
        budget_minutes=240,
        favorite_slugs={"sevkabel-port"},
        dismissed_slugs={"sevkabel-port"},
        start_latitude=sevkabel.latitude,
        start_longitude=sevkabel.longitude,
    )

    assert route is not None
    assert "sevkabel-port" not in {place.slug for place in route.places}


def test_personal_route_uses_visited_history_for_unseen_affinity() -> None:
    city = catalog()
    baseline = build_personal_route(
        city,
        ("museums",),
        budget_minutes=120,
        visited_slugs={"hermitage"},
    )
    ranked = recommend_personalized(
        city,
        ("museums",),
        limit=len(city.places),
        visited_slugs={"hermitage"},
        exclude_slugs={"hermitage"},
    )

    assert baseline is not None
    assert ranked
    assert baseline.places[0].slug == ranked[0].place.slug
    assert "hermitage" not in {place.slug for place in baseline.places}
    assert any(
        reason.startswith("похоже на посещённое:")
        for item in ranked
        for reason in item.reasons
    )


def test_personal_route_excludes_completed_stops_but_uses_their_affinity() -> None:
    city = catalog()
    route = build_personal_route(
        city,
        ("museums",),
        budget_minutes=240,
        completed_route_place_slugs={"hermitage"},
    )
    ranked = recommend_personalized(
        city,
        ("museums",),
        limit=len(city.places),
        completed_route_place_slugs={"hermitage"},
        exclude_slugs={"hermitage"},
    )

    assert route is not None
    assert "hermitage" not in {place.slug for place in route.places}
    assert route.places[0].slug == ranked[0].place.slug
    assert any(
        reason.startswith("похоже на пройденный маршрут:")
        for item in ranked
        for reason in item.reasons
    )


def test_explained_personal_route_keeps_reasons_for_selected_stops() -> None:
    result = build_explained_personal_route(
        catalog(),
        ("museums",),
        budget_minutes=240,
        completed_route_place_slugs={"hermitage"},
    )

    assert result is not None
    assert result.recommendations
    assert {item.place.slug for item in result.recommendations} == {
        place.slug for place in result.route.places
    }
    assert all(
        item.reasons and item.reasons[0] == "интерес: 🖼 Музеи"
        for item in result.recommendations
    )
    assert "hermitage" not in {
        place.slug for place in result.route.places
    }


def test_explained_personal_route_matches_compatibility_wrapper() -> None:
    kwargs = {
        "budget_minutes": 240,
        "favorite_slugs": {"new-holland"},
        "visited_slugs": {"summer-garden"},
        "dismissed_slugs": {"palace-square"},
    }
    explained = build_explained_personal_route(
        catalog(),
        ("walks", "free"),
        **kwargs,
    )
    route = build_personal_route(
        catalog(),
        ("walks", "free"),
        **kwargs,
    )

    assert explained is not None
    assert explained.route == route

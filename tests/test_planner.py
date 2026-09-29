import pytest

from app.catalog import get_catalog
from app.data.spb import CITY_SLUG
from app.planner import INTEREST_LABELS, build_route


def catalog():
    return get_catalog(CITY_SLUG)


@pytest.mark.parametrize("budget_minutes", [120, 240, 360])
@pytest.mark.parametrize("interest", tuple(INTEREST_LABELS))
def test_generated_route_never_exceeds_budget(
    budget_minutes: int,
    interest: str,
) -> None:
    route = build_route(
        catalog(),
        budget_minutes=budget_minutes,
        interest=interest,
    )

    assert route is not None
    assert route.places
    assert route.estimated_minutes <= budget_minutes


def test_architecture_route_contains_only_relevant_places() -> None:
    route = build_route(
        catalog(),
        budget_minutes=240,
        interest="architecture",
    )

    assert route is not None
    assert route.places
    assert all(
        "архитектура" in place.tags or "собор" in place.tags
        for place in route.places
    )


def test_free_route_contains_only_free_places() -> None:
    route = build_route(
        catalog(),
        budget_minutes=360,
        interest="free",
    )

    assert route is not None
    assert route.places
    assert all(place.is_free for place in route.places)


def test_family_route_contains_only_family_places() -> None:
    route = build_route(
        catalog(),
        budget_minutes=360,
        interest="family",
    )

    assert route is not None
    assert route.places
    assert all("с детьми" in place.tags for place in route.places)


def test_planner_is_deterministic() -> None:
    first = build_route(
        catalog(),
        budget_minutes=240,
        interest="classic",
    )
    second = build_route(
        catalog(),
        budget_minutes=240,
        interest="classic",
    )

    assert first == second


def test_two_hour_classic_route_has_multiple_stops() -> None:
    route = build_route(
        catalog(),
        budget_minutes=120,
        interest="classic",
    )

    assert route is not None
    assert len(route.places) >= 2
    assert route.estimated_minutes <= 120


def test_invalid_budget_fails_closed() -> None:
    with pytest.raises(ValueError, match="budget_minutes"):
        build_route(catalog(), budget_minutes=0, interest="classic")


def test_unknown_interest_fails_closed() -> None:
    with pytest.raises(ValueError, match="Unsupported interest"):
        build_route(catalog(), budget_minutes=120, interest="nightlife")


def test_location_origin_chooses_nearest_candidate() -> None:
    city = catalog()
    sevkabel = city.place_by_slug("sevkabel-port")
    assert sevkabel is not None

    without_location = build_route(
        city,
        budget_minutes=120,
        interest="unusual",
    )
    with_location = build_route(
        city,
        budget_minutes=120,
        interest="unusual",
        start_latitude=sevkabel.latitude,
        start_longitude=sevkabel.longitude,
    )

    assert without_location is not None
    assert with_location is not None
    assert without_location.places[0].slug == "new-holland"
    assert with_location.places[0].slug == "sevkabel-port"


def test_location_walk_is_included_in_budget_and_distance() -> None:
    route = build_route(
        catalog(),
        budget_minutes=120,
        interest="unusual",
        start_latitude=59.9200,
        start_longitude=30.2300,
    )

    assert route is not None
    assert route.places[0].slug == "sevkabel-port"
    assert route.distance_km > 0
    assert route.estimated_minutes > route.places[0].visit_minutes
    assert route.estimated_minutes <= route.budget_minutes


def test_far_origin_can_produce_no_route() -> None:
    route = build_route(
        catalog(),
        budget_minutes=120,
        interest="classic",
        start_latitude=55.7558,
        start_longitude=37.6176,
    )

    assert route is None


def test_partial_origin_fails_closed() -> None:
    with pytest.raises(ValueError, match="provided together"):
        build_route(
            catalog(),
            budget_minutes=120,
            interest="classic",
            start_latitude=59.93,
        )


def test_invalid_origin_range_fails_closed() -> None:
    with pytest.raises(ValueError, match="start_latitude"):
        build_route(
            catalog(),
            budget_minutes=120,
            interest="classic",
            start_latitude=100.0,
            start_longitude=30.0,
        )

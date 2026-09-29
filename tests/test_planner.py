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

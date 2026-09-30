from app.catalog import get_catalog
from app.place_route import build_place_route
from app.saved_routes import PLACE_ROUTE_INTEREST


def test_spb_place_route_keeps_origin_first_and_budget() -> None:
    route = build_place_route(
        get_catalog("saint-petersburg"),
        "hermitage",
        budget_minutes=240,
    )

    assert route is not None
    assert route.interest == PLACE_ROUTE_INTEREST
    assert route.places[0].slug == "hermitage"
    assert route.estimated_minutes <= route.budget_minutes
    slugs = tuple(place.slug for place in route.places)
    assert len(slugs) == len(set(slugs))


def test_perm_place_route_uses_same_generic_flow() -> None:
    route = build_place_route(
        get_catalog("perm"),
        "perm-bear",
        budget_minutes=240,
    )

    assert route is not None
    assert route.places[0].slug == "perm-bear"
    assert route.estimated_minutes <= 240
    assert len(route.places) >= 2


def test_place_route_is_deterministic() -> None:
    catalog = get_catalog("saint-petersburg")

    first = build_place_route(
        catalog,
        "summer-garden",
        budget_minutes=360,
    )
    second = build_place_route(
        catalog,
        "summer-garden",
        budget_minutes=360,
    )

    assert first == second


def test_unknown_origin_fails_closed() -> None:
    assert build_place_route(
        get_catalog("perm"),
        "missing-place",
        budget_minutes=240,
    ) is None


def test_origin_that_does_not_fit_budget_fails_closed() -> None:
    assert build_place_route(
        get_catalog("saint-petersburg"),
        "hermitage",
        budget_minutes=1,
    ) is None

from datetime import date

from app.catalog import distance_km
from app.domain import Place, PlaceSource
from app.planner import MAX_GENERATED_WALK_LEG_KM, build_ranked_route

SOURCE = PlaceSource("Test source", "https://example.org/", date(2026, 10, 8))


def place(slug: str, latitude: float, category: str = "sights") -> Place:
    return Place(
        slug,
        slug,
        category,
        "Example attraction",
        "🏛",
        "Central district",
        30,
        True,
        latitude,
        40.0,
        SOURCE,
        ("прогулка",),
    )


def test_generated_route_never_connects_remote_stops() -> None:
    origin = place("origin", 55.0)
    remote = place("remote", 55.20)
    route = build_ranked_route(
        (origin, remote), budget_minutes=600, route_interest="classic",
    )
    assert route is not None
    assert tuple(item.slug for item in route.places) == ("origin",)
    assert route.distance_km == 0


def test_ranked_planner_skips_remote_variety_in_favor_of_nearby() -> None:
    origin = place("origin", 55.0, "sights")
    remote = place("remote", 55.12, "museums")
    nearby = place("near", 55.003, "sights")
    route = build_ranked_route(
        (origin, remote, nearby),
        budget_minutes=600,
        route_interest="personal",
        prefer_variety=True,
    )
    assert route is not None
    assert tuple(item.slug for item in route.places) == ("origin", "near")
    assert distance_km(route.places[0], route.places[1]) < MAX_GENERATED_WALK_LEG_KM


def test_origin_outside_pedestrian_radius_fails_closed() -> None:
    attraction = place("attraction", 55.0)
    route = build_ranked_route(
        (attraction,),
        budget_minutes=600,
        route_interest="classic",
        start_latitude=55.25,
        start_longitude=40.0,
    )
    assert route is None


def test_origin_can_select_second_candidate_within_radius() -> None:
    remote = place("remote", 55.0)
    nearby = place("near", 55.12)
    route = build_ranked_route(
        (remote, nearby),
        budget_minutes=240,
        route_interest="classic",
        start_latitude=55.1205,
        start_longitude=40.0,
    )
    assert route is not None
    assert route.places[0].slug == "near"


def test_route_limit_is_independent_of_available_time() -> None:
    attraction = place("one", 55.0)
    remote = place("two", 55.10)
    assert distance_km(attraction, remote) > MAX_GENERATED_WALK_LEG_KM
    for budget in (120, 240, 1440):
        route = build_ranked_route(
            (attraction, remote), budget_minutes=budget, route_interest="walks",
        )
        assert route is not None
        assert len(route.places) == 1

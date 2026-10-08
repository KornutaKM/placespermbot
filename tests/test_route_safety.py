from datetime import date

from app.catalog import CityCatalog
from app.catalog_validation import validate_catalog
from app.domain import Place, PlaceSource, RoutePlan
from app.place_route import build_place_route
from app.planner import build_ranked_route
from app.route_safety import (
    is_route_stop_available,
    route_access_warnings,
    route_geography,
)

SOURCE = PlaceSource("Source", "https://example.org/place", date(2026, 10, 1))


def make_place(slug: str, lat: float, tags: tuple[str, ...] = ("история",)) -> Place:
    return Place(slug, slug, "sights", "Description", "🏛", "Center", 30,
                 True, lat, 40.0, SOURCE, tags)


def test_explicit_closed_tag_not_heuristic() -> None:
    assert is_route_stop_available(make_place("open", 55.0, ("закрытые витрины",)))
    assert not is_route_stop_available(make_place("closed", 55.0, ("закрыто",)))


def test_planner_filters_closed_first_and_subsequent_candidates() -> None:
    closed = make_place("closed", 55.0, ("закрыто",))
    opened = make_place("open", 55.001)
    route = build_ranked_route((closed, opened), budget_minutes=180, route_interest="classic")
    assert route is not None
    assert tuple(place.slug for place in route.places) == ("open",)
    assert build_ranked_route((closed,), budget_minutes=180, route_interest="classic") is None


def test_place_route_rejects_unavailable_origin() -> None:
    city = CityCatalog("test", "Test", {"sights": "Sights"},
                       (make_place("closed", 55.0, ("закрыто",)),
                        make_place("open", 55.001)), ())
    assert build_place_route(city, "closed", budget_minutes=180) is None


def test_curated_route_rejects_closed_stops() -> None:
    city = CityCatalog(
        "test", "Test", {"sights": "Sights"},
        (make_place("open", 55.0), make_place("closed", 55.001, ("закрыто",))),
        (RoutePlan("walk", "Walk", "Summary", 90, 1.0, ("open", "closed")),),
    )
    assert "route.place.unavailable" in {item.code for item in validate_catalog(city)}


def test_geography_flags_long_straight_line_not_travel_time() -> None:
    first = make_place("first", 55.0)
    second = make_place("second", 55.001)
    distant = make_place("distant", 55.25)
    report = route_geography((first, second, distant))
    assert report.longest_leg_km > 8
    assert report.straight_line_km >= report.longest_leg_km
    assert report.long_legs[0][:2] == ("second", "distant")
    assert "транспорт" in route_access_warnings((first, second, distant))[0]
    assert route_access_warnings((first, second)) == ()


def test_closed_status_warning() -> None:
    warnings = route_access_warnings((make_place("closed", 55.0, ("закрыто",)),))
    assert len(warnings) == 1
    assert "закрытыми" in warnings[0]

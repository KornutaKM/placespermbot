from dataclasses import replace

import pytest

from app.catalog import get_catalog, list_catalogs
from app.personal_route import PersonalRouteResult
from app.personal_route_ui import personal_route_result_text
from app.place_route import build_place_route
from app.planner import INTEREST_LABELS, build_route
from app.route_timing import route_timing, route_timing_text


@pytest.mark.parametrize("budget", (120, 240, 360))
@pytest.mark.parametrize("interest", tuple(INTEREST_LABELS))
def test_route_timing_breakdown_preserves_budget_and_visit_time(budget, interest):
    route = build_route(
        get_catalog("saint-petersburg"),
        budget_minutes=budget,
        interest=interest,
    )
    assert route is not None
    timing = route_timing(route)
    assert timing.visit_minutes == sum(place.visit_minutes for place in route.places)
    assert timing.walking_minutes >= 0
    assert timing.spare_minutes >= 0
    assert timing.visit_minutes + timing.walking_minutes == route.estimated_minutes
    assert route.estimated_minutes + timing.spare_minutes == budget
    assert "пешие переходы" in route_timing_text(route)


def test_route_breakdown_is_consistent_for_every_city():
    for catalog in list_catalogs():
        route = build_route(catalog, budget_minutes=240, interest="classic")
        assert route is not None, catalog.slug
        timing = route_timing(route)
        assert timing.visit_minutes + timing.walking_minutes + timing.spare_minutes == 240


def test_origin_walking_time_is_part_of_breakdown():
    city = get_catalog("saint-petersburg")
    place = city.place_by_slug("sevkabel-port")
    assert place is not None
    route = build_route(
        city,
        budget_minutes=120,
        interest="unusual",
        start_latitude=place.latitude + 0.004,
        start_longitude=place.longitude,
    )
    assert route is not None
    timing = route_timing(route)
    assert timing.walking_minutes > 0
    assert timing.visit_minutes + timing.walking_minutes == route.estimated_minutes


def test_place_anchored_route_uses_same_timing_contract():
    city = get_catalog("saint-petersburg")
    route = build_place_route(city, "hermitage", budget_minutes=240)
    assert route is not None
    timing = route_timing(route)
    assert timing.visit_minutes + timing.walking_minutes == route.estimated_minutes
    assert timing.spare_minutes == route.budget_minutes - route.estimated_minutes


def test_personal_route_text_includes_shared_breakdown():
    route = build_route(get_catalog("perm"), budget_minutes=240, interest="classic")
    assert route is not None
    result = PersonalRouteResult(route=route, recommendations=())
    text = personal_route_result_text(result, location_used=False)
    timing = route_timing(route)
    assert f"осмотр ~{timing.visit_minutes} мин" in text
    assert f"пешие переходы ~{timing.walking_minutes} мин" in text
    assert f"Резерв бюджета: ~{timing.spare_minutes} мин" in text


def test_timing_rejects_impossible_generated_route():
    route = build_route(get_catalog("perm"), budget_minutes=240, interest="classic")
    assert route is not None
    visits = sum(place.visit_minutes for place in route.places)
    with pytest.raises(ValueError, match="visit time"):
        route_timing(replace(route, estimated_minutes=visits - 1))
    with pytest.raises(ValueError, match="exceeds time budget"):
        route_timing(replace(route, estimated_minutes=route.budget_minutes + 1))

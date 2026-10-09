"""The route metric gate protects all city catalogs, not only one city."""

from app.catalog import list_catalogs
from app.route_review import HARD_ROUTE_CODES, collect_route_findings, hard_route_findings


def test_all_editorial_routes_have_physically_plausible_lower_bounds() -> None:
    catalogs = list_catalogs()
    assert len(catalogs) >= 32
    assert sum(len(city.routes) for city in catalogs) >= 305
    findings = collect_route_findings()
    assert hard_route_findings(findings) == ()
    assert not HARD_ROUTE_CODES.intersection(finding.code for finding in findings)


def test_far_apart_stops_remain_visible_as_advisory_review_signals() -> None:
    findings = collect_route_findings()
    assert all(
        finding.code == "long_straight_line_leg"
        for finding in findings
    )

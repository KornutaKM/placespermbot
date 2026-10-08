from datetime import date

from app.catalog import CityCatalog, list_catalogs
from app.catalog_coverage import (
    assess_catalog_coverage,
    collect_coverage,
    main,
    render_coverage_markdown,
)
from app.domain import Place, PlaceSource, RoutePlan


def _city_with_known_routes() -> CityCatalog:
    places = tuple(
        Place(
            f"place-{index}",
            f"Place {index}",
            "sights",
            "Safe to visit on public space",
            "🏛",
            "Centre",
            60,
            True,
            55.0 + index / 100,
            49.0,
            PlaceSource("Local government", "https://example.org/museum", date(2026, 10, 8)),
            ("family", "с детьми"),
        )
        for index in range(3)
    )
    return CityCatalog(
        "test-city",
        "Test City",
        {"sights": "Sights"},
        places,
        (RoutePlan("walk", "Walk", "A short route", 180, 2.0, ("place-0", "place-1")),),
    )


def test_coverage_calculates_distinct_reachable_places_and_geodesic() -> None:
    coverage = assess_catalog_coverage(_city_with_known_routes())
    assert coverage.places == 3
    assert coverage.places_used_by_routes == 2
    assert coverage.route_coverage_percent == 67
    assert coverage.max_consecutive_leg_km > 1.0
    assert coverage.max_consecutive_leg_km < 1.2
    assert coverage.source_domains == 1
    assert "single_source_domain" in coverage.signals
    assert "category_gap" in coverage.signals
    assert "single_stop_routes" not in coverage.signals


def test_coverage_is_safe_for_missing_references_and_empty_city() -> None:
    empty = CityCatalog("empty", "Empty", {}, (), ())
    coverage = assess_catalog_coverage(empty)
    assert coverage.places_used_by_routes == 0
    assert coverage.route_coverage_percent == 0
    assert coverage.max_consecutive_leg_km == 0

    city = _city_with_known_routes()
    broken = CityCatalog(
        city.slug,
        city.name,
        city.category_labels,
        city.places,
        (RoutePlan("broken", "Broken", "No duplicate", 60, 1.0, ("gone",)),),
    )
    result = assess_catalog_coverage(broken)
    assert result.single_stop_routes == 1
    assert "single_stop_routes" in result.signals
    assert result.places_used_by_routes == 0


def test_coverage_reports_all_registered_cities_in_stable_priority_order() -> None:
    rows = collect_coverage()
    assert len(rows) == len(list_catalogs())
    assert {row.city for row in rows} == {catalog.slug for catalog in list_catalogs()}
    assert list(rows) == sorted(rows, key=lambda row: (-len(row.signals), row.places, row.city))
    assert all(0 <= row.route_coverage_percent <= 100 for row in rows)
    assert all(0 <= row.places_used_by_routes <= row.places for row in rows)
    assert all(row.max_consecutive_leg_km >= 0 for row in rows)
    markdown = render_coverage_markdown(rows)
    assert "## City catalog coverage" in markdown
    assert markdown.count("|") > 100


def test_coverage_cli_json_and_markdown(capsys) -> None:
    main(["--format", "json"])
    json_result = capsys.readouterr().out
    assert '"route_coverage_percent"' in json_result
    assert '"source_domains"' in json_result
    main(["--format", "markdown"])
    markdown = capsys.readouterr().out
    assert "City catalog coverage" in markdown

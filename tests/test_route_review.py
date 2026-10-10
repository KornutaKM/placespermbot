from datetime import date

from app.catalog import CityCatalog, list_catalogs
from app.domain import Place, PlaceSource, RoutePlan
from app.route_transport import (
    REVIEWED_TRANSFERS,
    audit_reviewed_transfers,
    detect_long_transfers,
    route_requires_transport,
    transfer_notes,
)
from app.route_review import (
    collect_route_findings,
    inspect_routes,
    main,
    render_route_review,
)

SOURCE = PlaceSource("Test source", "https://example.org/", date(2026, 10, 1))


def place(name: str, lat: float) -> Place:
    return Place(name, name, "sights", "Summary", "🏛", "Centre",
                 60, True, lat, 40.0, SOURCE, ("history",))


def test_review_exposes_long_leg_and_unrealistic_distance() -> None:
    city = CityCatalog(
        "test", "Test", {"sights": "Sights"},
        (place("near", 55.0), place("far", 55.25)),
        (RoutePlan("walk", "Walk", "Description", 90, 1.0, ("near", "far")),),
    )
    findings = inspect_routes(city)
    assert {f.code for f in findings} == {
        "long_straight_line_leg",
        "distance_below_geodesic_minimum",
        "duration_below_visit_time",
    }
    assert all(f.city == "test" and f.route == "walk" for f in findings)
    assert all(f.declared_km == 1.0 for f in findings)
    assert findings[0].first_stop == "near"
    assert findings[0].next_stop == "far"


def test_review_does_not_flag_sensible_short_walk() -> None:
    city = CityCatalog(
        "test", "Test", {"sights": "Sights"},
        (place("one", 55.0), place("two", 55.0005)),
        (RoutePlan("walk", "Walk", "Description", 150, 0.5, ("one", "two")),),
    )
    assert inspect_routes(city) == ()


def test_review_ignores_deleted_route_stops_and_empty_catalog() -> None:
    empty = CityCatalog("test", "Test", {}, (), ())
    assert inspect_routes(empty) == ()
    broken = CityCatalog(
        "test", "Test", {"sights": "Sights"},
        (place("one", 55.0),),
        (RoutePlan("walk", "Walk", "Description", 100, 0.5, ("one", "missing")),),
    )
    assert inspect_routes(broken) == ()


def test_review_scans_every_registered_catalog_deterministically() -> None:
    first = collect_route_findings()
    second = collect_route_findings()
    assert first == second
    slugs = {catalog.slug for catalog in list_catalogs()}
    assert {finding.city for finding in first} <= slugs
    assert list(first) == sorted(
        first, key=lambda f: (f.city, f.route, f.code, f.first_stop),
    )
    assert "Editorial route geography review" in render_route_review(first)


def test_route_review_cli_outputs_json_and_markdown(capsys) -> None:
    main(["--format", "json"])
    assert capsys.readouterr().out.lstrip().startswith("[")
    main(["--format", "markdown"])
    assert "Potential issues to review:" in capsys.readouterr().out


def test_all_long_transfers_are_explicitly_reviewed() -> None:
    actual = detect_long_transfers(list_catalogs())
    assert len(actual) == 9
    assert actual == set(REVIEWED_TRANSFERS)
    assert audit_reviewed_transfers(list_catalogs()) == ((), ())
    assert route_requires_transport("moscow", "moscow-modern")
    assert transfer_notes("sochi", "sochi-matsesta-nature")
    assert not route_requires_transport("sochi", "sochi-first-walk")


def test_long_transfer_registry_detects_new_and_obsolete_legs() -> None:
    from app.catalog import get_catalog
    from app.domain import RoutePlan

    city = get_catalog("moscow")
    changed_routes = tuple(
        RoutePlan(
            route.slug, route.title, route.summary, route.duration_minutes,
            route.distance_km, ("red-square", "vdnh"),
        ) if route.slug == "moscow-modern" else route
        for route in city.routes
    )
    edited = CityCatalog(
        city.slug, city.name, city.category_labels, city.places, changed_routes,
    )
    missing, obsolete = audit_reviewed_transfers(
        (catalog for catalog in list_catalogs() if catalog.slug != "moscow")
    )
    assert missing == ()
    assert all(city_slug == "moscow" for city_slug, *_ in obsolete)
    missing, obsolete = audit_reviewed_transfers(
        (*(
            catalog for catalog in list_catalogs()
            if catalog.slug != "moscow"
        ), edited),
    )
    assert missing
    assert ("moscow", "moscow-modern", "vdnh", "moscow-city") in obsolete

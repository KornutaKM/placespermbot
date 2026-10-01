from datetime import date, timedelta

from app.catalog import CityCatalog
from app.catalog_validation import validate_catalog
from app.domain import Place, PlaceSource, RoutePlan

SOURCE = PlaceSource("Source", "https://example.com/place", date(2026, 10, 1))


def test_validator_accepts_valid_catalog() -> None:
    catalog = CityCatalog(
        slug="city",
        name="City",
        category_labels={"sights": "Sights"},
        places=(Place("one", "One", "sights", "Summary", "🏛", "Center", 30, True, 50.0, 30.0, SOURCE),),
        routes=(RoutePlan("walk", "Walk", "Summary", 60, 1.0, ("one",)),),
    )

    assert validate_catalog(catalog) == ()


def test_validator_reports_broken_catalog_invariants() -> None:
    bad_source = PlaceSource("", "http://example.com/place", date(2026, 10, 1))
    place = Place("same", "One", "missing", "Summary", "🏛", "Center", 0, True, 95.0, 30.0, bad_source)
    catalog = CityCatalog(
        slug="city",
        name="City",
        category_labels={"sights": "Sights"},
        places=(place, place),
        routes=(RoutePlan("walk", "Walk", "Summary", 0, 0.0, ("same", "same", "unknown")),),
    )

    codes = {issue.code for issue in validate_catalog(catalog)}

    assert "place.slug.duplicate" in codes
    assert "place.category.unknown" in codes
    assert "place.visit.invalid" in codes
    assert "place.coordinates.invalid" in codes
    assert "place.source.invalid" in codes
    assert "place.source.name.empty" in codes
    assert "route.metrics.invalid" in codes
    assert "route.place.missing" in codes
    assert "route.place.duplicate" in codes


def test_validator_rejects_future_stale_and_known_irrelevant_sources() -> None:
    today = date.today()
    sources = (
        PlaceSource("Future", "https://example.com/future", today + timedelta(days=1)),
        PlaceSource("Stale", "https://example.com/stale", today - timedelta(days=367)),
        PlaceSource(
            "Unrelated",
            "https://visit-kaliningrad.ru/tourism/lechebnaya-verkhovaya-ezda/",
            today,
        ),
    )
    places = tuple(
        Place(
            f"place-{index}",
            f"Place {index}",
            "sights",
            "Summary",
            "🏛",
            "Center",
            30,
            True,
            50.0,
            30.0,
            source,
        )
        for index, source in enumerate(sources)
    )
    catalog = CityCatalog(
        slug="city",
        name="City",
        category_labels={"sights": "Sights"},
        places=places,
        routes=(RoutePlan("walk", "Walk", "Summary", 60, 1.0, tuple(place.slug for place in places)),),
    )

    codes = {issue.code for issue in validate_catalog(catalog)}

    assert "place.source.checked_at.future" in codes
    assert "place.source.checked_at.stale" in codes
    assert "place.source.irrelevant" in codes

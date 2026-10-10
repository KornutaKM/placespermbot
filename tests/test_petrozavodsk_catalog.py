from datetime import date

from app.catalog import get_catalog
from app.catalog_quality import validate_catalog_quality
from app.city_manifest import list_city_manifests
from app.route_review import hard_route_findings, inspect_routes


def test_petrozavodsk_city_catalog_and_quality() -> None:
    city = get_catalog("petrozavodsk")
    manifest = next(m for m in list_city_manifests() if m.slug == city.slug)
    assert len(city.places) == 28
    assert len(city.routes) == 11
    assert len({p.category for p in city.places}) == 5
    assert sum(p.category == "museums" for p in city.places) >= 8
    assert validate_catalog_quality(city, manifest.quality) == ()
    assert hard_route_findings(inspect_routes(city)) == ()


def test_petrozavodsk_city_kizhi_access_and_search() -> None:
    city = get_catalog("petrozavodsk")
    museum = city.place_by_slug("ptz-kizhi-halls")
    assert museum is not None
    assert "не входит" in museum.summary
    assert city.place_by_slug("ptz-kizhi-children").latitude < 62
    assert city.search_places("Полярный Одиссей")[0].slug == "ptz-odyssey"
    free = {p.slug for p in city.places_for_category("free")}
    assert "ptz-onega" in free
    assert "ptz-kizhi-halls" not in free
    assert all(p.source.checked_at == date(2026, 10, 9) for p in city.places)

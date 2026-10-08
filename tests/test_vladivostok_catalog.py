from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog


def test_vladivostok_expansion_museums_and_sources() -> None:
    city = get_catalog("vladivostok")
    assert len(city.places) >= 32
    assert len(city.routes) >= 13
    assert len({p.category for p in city.places}) == 5
    assert len({p.district for p in city.places}) >= 12
    assert sum(p.category == "museums" for p in city.places) >= 8
    for slug, host in {
        "vvo-fortress-visitor-centre": "fortressvl.ru",
        "vvo-primorsky-art-gallery": "www.culture.ru",
        "vvo-pacific-fleet-museum": "www.culture.ru",
    }.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert place.source.checked_at == date(2026, 10, 8)
        assert urlparse(place.source.url).hostname == host


def test_vladivostok_fortress_rules_and_locality() -> None:
    city = get_catalog("vladivostok")
    underground = city.place_by_slug("vvo-fortress-underground-excursion")
    battery = city.place_by_slug("vvo-russky-fort-exterior")
    assert underground is not None and battery is not None
    assert "только в составе" in underground.summary
    assert "с экскурсией" in battery.summary
    assert not underground.is_free and not battery.is_free
    assert city.search_places("Тихоокеанского флота")[0].slug == "vvo-pacific-fleet-museum"
    assert "vvo-cesarevich-embankment" in {p.slug for p in city.places_for_category("free")}
    assert "vvo-primorsky-art-gallery" in {p.slug for p in city.places_for_category("family")}
    for slug in ("vvo-russky-island", "vvo-family-nature"):
        route = city.route_by_slug(slug)
        assert route is not None and "транспорт" in route.summary
    assert all(len(r.place_slugs) >= 2 for r in city.routes)

from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog


def test_yekaterinburg_coverage_and_official_institutions() -> None:
    city = get_catalog("yekaterinburg")
    assert len(city.places) >= 28
    assert len(city.routes) >= 13
    assert len({p.district for p in city.places}) >= 10
    assert len({p.category for p in city.places}) == 5
    assert sum(p.category == "museums" for p in city.places) >= 10
    for slug, domain in {
        "ekb-metenkov-temporary": "dommetenkova.ru",
        "ekb-architecture-museum": "museumarch.ru",
        "ekb-hermitage-ural": "i-z-o.art",
        "ekb-mayakovsky-park": "xn--e1agfrc5b.xn--p1ai",
    }.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert place.source.checked_at == date(2026, 10, 8)
        assert urlparse(place.source.url).hostname == domain


def test_yekaterinburg_museum_temporary_site_and_family_routes() -> None:
    city = get_catalog("yekaterinburg")
    photo = city.place_by_slug("ekb-metenkov-temporary")
    assert photo is not None
    assert "Тургенева, 15" in photo.summary
    assert "ремонта" in photo.summary
    assert not photo.is_free
    assert city.search_places("Парк имени Маяковского")[0].slug == "ekb-mayakovsky-park"
    family = {p.slug for p in city.places_for_category("family")}
    assert {"ekb-mayakovsky-park", "ekb-naive-art", "ekb-ural-minerals-showcase"} <= family
    route = city.route_by_slug("ekb-art-museums")
    assert route is not None
    assert photo.slug in route.place_slugs
    assert all(len(route.place_slugs) >= 2 for route in city.routes)

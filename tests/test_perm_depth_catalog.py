from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog


def test_perm_expanded_catalog_and_official_sources() -> None:
    city = get_catalog("perm")
    assert len(city.places) >= 31
    assert len(city.routes) >= 14
    assert len({p.category for p in city.places}) == 5
    assert len({p.district for p in city.places}) >= 10
    assert sum(p.category == "museums" for p in city.places) >= 7
    for slug, host in {
        "perm-underground-printshop": "museumperm.ru",
        "perm-museum-ancient-family": "museumperm.ru",
        "perm-motovilikha-pond": "www.gorodperm.ru",
    }.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert place.source.checked_at == date(2026, 10, 8)
        assert urlparse(place.source.url).hostname == host


def test_perm_family_museum_routes_and_provenance() -> None:
    city = get_catalog("perm")
    typography = city.place_by_slug("perm-underground-printshop")
    ancient = city.place_by_slug("perm-museum-ancient-family")
    assert typography is not None and ancient is not None
    assert "предварительной заявке" in typography.summary
    assert "четвёртом этаже" in ancient.summary
    assert not typography.is_free and not ancient.is_free
    assert city.search_places("Подпольная типография")[0].slug == typography.slug
    assert "perm-gorky-rotunda" in {p.slug for p in city.places_for_category("free")}
    assert "perm-museum-ancient-family" in {p.slug for p in city.places_for_category("family")}
    route = city.route_by_slug("perm-history-cathedral")
    assert route is not None and "perm-peter-paul-cathedral" in route.place_slugs
    assert all(len(route.place_slugs) >= 2 for route in city.routes)

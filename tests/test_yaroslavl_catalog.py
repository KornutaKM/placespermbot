from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog


def test_yaroslavl_expanded_discovery_and_official_sources() -> None:
    city = get_catalog("yaroslavl")
    assert len(city.places) >= 28
    assert len(city.routes) >= 10
    assert len({place.category for place in city.places}) >= 5
    assert len({place.district for place in city.places}) >= 10
    assert sum(place.category == "museums" for place in city.places) >= 8
    sources = {
        "yar-tereshkova-planetarium": "yarplaneta.ru",
        "yar-john-baptist-tolchkov": "www.yarkremlin.ru",
        "yar-max-bogdanovich-museum": "mukmig.yaroslavl.ru",
        "yar-music-time-museum": "www.culture.ru",
        "yar-volkov-theatre": "www.volkovteatr.ru",
    }
    for slug, host in sources.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert place.source.checked_at == date(2026, 10, 8)
        assert urlparse(place.source.url).hostname == host


def test_yaroslavl_closed_tolchkov_not_in_routes() -> None:
    city = get_catalog("yaroslavl")
    place = city.place_by_slug("yar-john-baptist-tolchkov")
    assert place is not None
    assert "закрыт" in place.title.casefold()
    assert "не входите за ограждения" in place.summary
    assert not place.is_free
    assert all(place.slug not in route.place_slugs for route in city.routes)
    assert "yar-tereshkova-planetarium" in {
        item.slug for item in city.places_for_category("family")
    }
    assert "yar-max-bogdanovich-museum" in {
        item.slug for item in city.places_for_category("family")
    }
    assert city.search_places("Нужина")[0].slug == "yar-nuzhin-exhibition-hall"
    routes = {route.slug: route for route in city.routes}
    assert "yar-volkov-quarter" in routes
    assert "yar-river-heritage" in routes
    assert "yar-science-family" in routes
    assert all(len(route.place_slugs) >= 2 for route in city.routes)

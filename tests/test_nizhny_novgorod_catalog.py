from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog


def test_nizhny_expanded_catalog_and_new_sources() -> None:
    city = get_catalog("nizhny-novgorod")
    assert len(city.places) >= 31
    assert len(city.routes) >= 13
    assert len({p.category for p in city.places}) == 5
    assert len({p.district for p in city.places}) >= 10
    assert len([p for p in city.places if p.category == "museums"]) >= 10
    for slug, host in {
        "nn-gorky-apartment": "museumgorkogo.ru",
        "nn-kashirin-house": "www.museumgorkogo.ru",
        "nn-technical-museum": "ngiamz.ru",
        "nn-closed-crafts-museum": "ngiamz.ru",
        "nn-cable-station-exterior": "nnkd.ru",
    }.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert place.source.checked_at == date(2026, 10, 8)
        assert urlparse(place.source.url).hostname == host


def test_nizhny_family_search_closed_sites_and_routes() -> None:
    city = get_catalog("nizhny-novgorod")
    assert city.search_places("Домик Каширина")[0].slug == "nn-kashirin-house"
    assert city.search_places("Русский музей фотографии")[0].slug == "nn-photography-museum"
    family = {p.slug for p in city.places_for_category("family")}
    free = {p.slug for p in city.places_for_category("free")}
    assert {"nn-toy-museum", "nn-kashirin-house", "nn-switzerland-viewpoint"} <= family
    assert "nn-cable-station-exterior" in free
    for closed in ("nn-closed-crafts-museum", "nn-gorky-literary-closed"):
        place = city.place_by_slug(closed)
        assert place is not None
        assert "закрыт" in place.summary
        assert not place.is_free
        assert all(closed not in route.place_slugs for route in city.routes)
    cable = city.place_by_slug("nn-cable-station-exterior")
    assert cable is not None and "приостановку движения" in cable.summary
    assert all(cable.slug not in route.place_slugs for route in city.routes)
    route = city.route_by_slug("nizhny-family-green")
    assert route is not None
    assert len(route.place_slugs) >= 3

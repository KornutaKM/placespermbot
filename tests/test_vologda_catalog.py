from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog

CITY_SLUG = "vologda"


def catalog():
    return get_catalog(CITY_SLUG)


def test_vologda_catalog_depth_and_geography() -> None:
    city = catalog()
    assert len(city.places) >= 33
    assert len(city.routes) >= 10
    assert len({p.district for p in city.places}) >= 10
    for place in city.places:
        assert 59.19 <= place.latitude <= 59.28
        assert 39.82 <= place.longitude <= 39.94
        assert place.source.checked_at == date(2026, 10, 8)
        parsed = urlparse(place.source.url)
        assert parsed.scheme == "https" and parsed.hostname


def test_vologda_official_sources_and_local_provenance() -> None:
    city = catalog()
    hosts = {
        "vologda-kremlin": "turvologda.ru",
        "vologda-lace-museum": "turvologda.ru",
        "vologda-sophia-cathedral": "turvologda.ru",
        "vologda-peter-house": "turvologda.ru",
        "vologda-art-gallery": "vologda-gallery.ru",
        "vologda-forgotten-things": "www.culture.ru",
        "vologda-exile-museum": "www.culture.ru",
        "vologda-letter-o": "turvologda.ru",
        "vologda-petrushka-theatre": "turvologda.ru",
        "spaso-prilutsky-monastery": "www.spas-priluki.ru",
    }
    for slug, host in hosts.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert urlparse(place.source.url).hostname == host


def test_vologda_search_and_free_family() -> None:
    city = catalog()
    assert city.search_places("Музей кружева")[0].slug == "vologda-lace-museum"
    assert city.search_places("букве «О»")[0].slug == "vologda-letter-o"
    family = {p.slug for p in city.places_for_category("family")}
    assert {
        "vologda-lace-museum", "vologda-childhood-museum",
        "vologda-petrushka-theatre", "vologda-park-mira",
        "vologda-carved-palisade",
    } <= family
    free = city.places_for_category("free")
    assert len(free) >= 19
    assert all(p.is_free for p in free)


def test_vologda_routes_cover_independent_scenarios() -> None:
    city = catalog()
    routes = {r.slug: r for r in city.routes}
    assert {
        "vologda-first-visit", "vologda-lace-crafts",
        "vologda-old-wood", "vologda-museum-marathon",
        "vologda-peter-merchants", "vologda-family",
        "vologda-river-churches", "vologda-greens",
        "vologda-literature-art", "vologda-north-monastery",
    } <= routes.keys()
    assert "vologda-lace-museum" in routes["vologda-first-visit"].place_slugs
    assert "vologda-zasetsky-house" in routes["vologda-old-wood"].place_slugs
    assert "vologda-petrushka-theatre" in routes["vologda-family"].place_slugs
    assert "spaso-prilutsky-monastery" in routes["vologda-north-monastery"].place_slugs
    known = {p.slug for p in city.places}
    for route in city.routes:
        assert route.duration_minutes > 0 and route.distance_km > 0
        assert set(route.place_slugs) <= known
        assert len(route.place_slugs) == len(set(route.place_slugs))


def test_vologda_heritage_conservation_and_visiting_not_guaranteed() -> None:
    city = catalog()
    kremlin = city.place_by_slug("vologda-kremlin")
    house = city.place_by_slug("vologda-zasetsky-house")
    belfry = city.place_by_slug("vologda-sophia-bell-tower")
    assert kremlin is not None and house is not None and belfry is not None
    assert "Архиерейского двора" in kremlin.summary
    assert "не обещается" in house.summary
    assert "только по фактическому режиму" in belfry.summary
    monastery = city.place_by_slug("spaso-prilutsky-monastery")
    childhood = city.place_by_slug("vologda-childhood-museum")
    assert monastery is not None and childhood is not None
    assert monastery.latitude > 59.26
    assert childhood.longitude < 39.88

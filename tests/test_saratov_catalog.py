from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog

CITY_SLUG = "saratov"


def catalog():
    return get_catalog(CITY_SLUG)


def test_saratov_catalog_geography_and_fresh_provenance() -> None:
    city = catalog()
    assert len(city.places) >= 25
    assert len(city.routes) >= 8
    for place in city.places:
        assert 51.48 <= place.latitude <= 51.60
        assert 45.90 <= place.longitude <= 46.09
        assert place.source.checked_at == date(2026, 10, 8)
        source = urlparse(place.source.url)
        assert source.scheme == "https"
        assert source.hostname


def test_saratov_museums_have_independent_official_provenance() -> None:
    city = catalog()
    expected_hosts = {
        "radishchev-art-museum": "radmuseumart.ru",
        "saratov-local-museum": "www.comk.ru",
        "chernyshevsky-estate": "sarusadba.ru",
        "fedin-museum": "fedinmuseum.ru",
        "borisov-musatov-estate": "radmuseumart.ru",
        "pavel-kuznetsov-house": "radmuseumart.ru",
        "military-labor-museum": "www.sargmbs.ru",
        "saratov-nikitin-circus": "www.circus-saratov.ru",
    }
    for slug, hostname in expected_hosts.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert urlparse(place.source.url).hostname == hostname


def test_saratov_search_and_virtual_family_free_categories() -> None:
    city = catalog()
    assert city.search_places("Радищевский")[0].slug == "radishchev-art-museum"
    assert city.search_places("Журавли")[0].slug == "cranes-memorial"
    family = {place.slug for place in city.places_for_category("family")}
    assert {
        "saratov-nikitin-circus",
        "saratov-children-park",
        "cosmonauts-embankment",
        "national-village",
        "saratov-harmonica-monument",
    } <= family
    free = city.places_for_category("free")
    assert len(free) >= 16
    assert all(place.is_free for place in free)


def test_saratov_routes_cover_museums_volga_family_and_memory() -> None:
    city = catalog()
    routes = {route.slug: route for route in city.routes}
    assert {
        "sar-first-walk", "sar-volga-history", "sar-art-museums",
        "sar-literary", "sar-family-center", "sar-victory-hill",
        "sar-green-south", "sar-unusual-center",
    } <= routes.keys()
    assert "radishchev-art-museum" in routes["sar-art-museums"].place_slugs
    assert "cosmonauts-embankment" in routes["sar-volga-history"].place_slugs
    assert "saratov-nikitin-circus" in routes["sar-family-center"].place_slugs
    assert "cranes-memorial" in routes["sar-victory-hill"].place_slugs
    for route in city.routes:
        assert route.duration_minutes > 0 and route.distance_km > 0
        assert len(set(route.place_slugs)) == len(route.place_slugs)


def test_saratov_park_and_estate_coordinates_are_separated() -> None:
    city = catalog()
    forest = city.place_by_slug("kumysnaya-polyana")
    embankment = city.place_by_slug("cosmonauts-embankment")
    assert forest is not None and embankment is not None
    assert forest.longitude < 46.0
    assert embankment.longitude > 46.04

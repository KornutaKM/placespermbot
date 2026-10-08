from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog

CITY_SLUG = "arkhangelsk"


def catalog():
    return get_catalog(CITY_SLUG)


def test_arkhangelsk_city_catalog_and_provenance() -> None:
    city = catalog()
    assert len(city.places) >= 30
    assert len(city.routes) >= 9
    assert len({p.district for p in city.places}) >= 10
    for place in city.places:
        assert 64.50 <= place.latitude <= 64.59
        assert 40.48 <= place.longitude <= 40.57
        assert place.source.checked_at == date(2026, 10, 8)
        parsed = urlparse(place.source.url)
        assert parsed.scheme == "https" and parsed.hostname


def test_arkhangelsk_specific_institution_sources() -> None:
    city = catalog()
    hosts = {
        "arkh-regional-museum": "pomorland.travel",
        "arkh-children-object-lab": "pomorland.travel",
        "arkh-nature-arctic-exhibition": "pomorland.travel",
        "northern-sea-museum-arkh": "northernmaritime.ru",
        "arkh-borisov-museum": "arhmuseum.ru",
        "arkh-pisakhov-museum": "arhmuseum.ru",
        "arkh-plotnikova-manor": "arhmuseum.ru",
        "arkh-kunitsyna-manor": "pomorland.travel",
        "arkh-commercial-assembly-house": "www.korely.ru",
    }
    for slug, host in hosts.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert urlparse(place.source.url).hostname == host


def test_arkhangelsk_free_family_and_search() -> None:
    city = catalog()
    assert city.search_places("Северный морской музей")[0].slug == "northern-sea-museum-arkh"
    assert city.search_places("Писахова")[0].slug == "arkh-pisakhov-museum"
    family = {p.slug for p in city.places_for_category("family")}
    assert {
        "arkh-children-object-lab", "arkh-poteshny-dvor",
        "arkh-kozuli-museum", "arkh-chumbarovka-pedestrian",
        "arkh-nature-arctic-exhibition",
    } <= family
    free = city.places_for_category("free")
    assert len(free) >= 16
    assert all(p.is_free for p in free)


def test_arkhangelsk_routes_and_transport_locality() -> None:
    city = catalog()
    routes = {r.slug: r for r in city.routes}
    assert {
        "arkh-first-visit", "arkh-maritime", "arkh-pomorskaya-museums",
        "arkh-family-museum", "arkh-wooden-streets", "arkh-arctic-history",
        "arkh-embankment-walk", "arkh-northern-art", "arkh-solombala",
    } <= routes.keys()
    assert "northern-sea-museum-arkh" in routes["arkh-maritime"].place_slugs
    assert "arkh-pisakhov-museum" in routes["arkh-pomorskaya-museums"].place_slugs
    assert "arkh-solombala-viewpoint" in routes["arkh-solombala"].place_slugs
    known = {p.slug for p in city.places}
    for route in city.routes:
        assert set(route.place_slugs) <= known
        assert len(route.place_slugs) == len(set(route.place_slugs))
        assert route.duration_minutes > 0 and route.distance_km > 0


def test_arkhangelsk_excludes_out_of_city_malye_korely_and_access_safety() -> None:
    city = catalog()
    assert not any("Малые Корелы" in p.title and "Коммерческого" not in p.title for p in city.places)
    museum = city.place_by_slug("arkh-children-object-lab")
    park = city.place_by_slug("arkh-poteshny-dvor")
    assert museum is not None and park is not None
    assert "мае 2026 года" in museum.summary
    assert "зависит от сезона" in park.summary

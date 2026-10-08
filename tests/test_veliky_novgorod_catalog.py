from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog

CITY_SLUG = "veliky-novgorod"


def catalog():
    return get_catalog(CITY_SLUG)


def test_veliky_novgorod_deep_catalog_and_current_sources() -> None:
    city = catalog()
    assert len(city.places) >= 30
    assert len(city.routes) >= 9
    for place in city.places:
        assert 58.46 <= place.latitude <= 58.56
        assert 31.25 <= place.longitude <= 31.32
        assert place.source.checked_at == date(2026, 10, 8)
        parsed = urlparse(place.source.url)
        assert parsed.scheme == "https" and parsed.hostname


def test_veliky_novgorod_institution_sources() -> None:
    city = catalog()
    sources = {
        "novgorod-detinets": "novgorodmuseum.ru",
        "novgorod-historic-museum": "novgorodmuseum.ru",
        "faceted-chamber-novgorod": "novgorodmuseum.ru",
        "museum-writing-novgorod": "novgorodmuseum.ru",
        "vitoslavlitsy-wooden-museum": "novgorodmuseum.ru",
        "yaroslav-court": "www.visitnovgorod.ru",
        "spas-ilina-church": "www.visitnovgorod.ru",
    }
    for slug, host in sources.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert urlparse(place.source.url).hostname == host


def test_veliky_novgorod_search_family_and_free() -> None:
    city = catalog()
    assert city.search_places("Детинец")[0].slug == "novgorod-detinets"
    assert city.search_places("Витославлицы")[0].slug == "vitoslavlitsy-wooden-museum"
    family = {p.slug for p in city.places_for_category("family")}
    assert {
        "children-museum-centre", "vitoslavlitsy-wooden-museum",
        "sokoliny-dvor", "kremlin-park-novgorod", "great-bridge-museum",
    } <= family
    free = city.places_for_category("free")
    assert len(free) >= 16
    assert all(p.is_free for p in free)


def test_veliky_novgorod_routes_cover_both_banks_and_suburbs() -> None:
    city = catalog()
    routes = {route.slug: route for route in city.routes}
    assert {
        "nov-first-walk", "nov-sofia-museums", "nov-trading-side",
        "nov-frescoes", "nov-family-centre", "nov-north-antonovo",
        "nov-wooden-culture", "nov-waterfront", "nov-art-and-craft",
    } <= routes.keys()
    assert "st-sophia-cathedral-novgorod" in routes["nov-first-walk"].place_slugs
    assert "yuriev-monastery-novgorod" in routes["nov-wooden-culture"].place_slugs
    assert "spas-ilina-church" in routes["nov-frescoes"].place_slugs
    assert "sokoliny-dvor" in routes["nov-family-centre"].place_slugs
    known = {p.slug for p in city.places}
    for route in city.routes:
        assert route.duration_minutes > 0 and route.distance_km > 0
        assert set(route.place_slugs) <= known
        assert len(route.place_slugs) == len(set(route.place_slugs))


def test_veliky_novgorod_provenance_and_access_safe() -> None:
    city = catalog()
    spaso = city.place_by_slug("spas-ilina-church")
    kokuy = city.place_by_slug("kokuy-tower-novgorod")
    belfry = city.place_by_slug("st-sophia-belfry")
    central = city.place_by_slug("yaroslav-court")
    outside = city.place_by_slug("vitoslavlitsy-wooden-museum")
    assert all(p is not None for p in (spaso, kokuy, belfry, central, outside))
    assert "режима доступа" in spaso.summary
    assert "внешний осмотр" in kokuy.summary
    assert "отдельный режим" in belfry.summary
    assert outside.latitude < central.latitude

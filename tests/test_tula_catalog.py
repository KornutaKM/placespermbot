from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog

CITY_SLUG = "tula"


def catalog():
    return get_catalog(CITY_SLUG)


def test_tula_has_deep_citywide_coverage_and_current_sources() -> None:
    city = catalog()
    assert len(city.places) >= 28
    assert len(city.routes) >= 8
    assert len({place.district for place in city.places}) >= 10
    for place in city.places:
        assert 54.15 <= place.latitude <= 54.25
        assert 37.56 <= place.longitude <= 37.69
        assert place.source.checked_at == date(2026, 10, 8)
        parsed = urlparse(place.source.url)
        assert parsed.scheme == "https" and parsed.hostname


def test_tula_institution_specific_official_sources() -> None:
    city = catalog()
    hosts = {
        "tula-weapons-helmet": "museum-arms.ru",
        "kremlin-epiphany-cathedral": "museum-arms.ru",
        "tula-samovars-museum": "museum-tula.ru",
        "tula-local-history-museum": "museum-tula.ru",
        "tula-demidov-museum": "museum-tula.ru",
        "veresaev-house-museum": "museum-tula.ru",
        "tula-antiquities": "kulpole.ru",
        "tula-machine-museum": "oktavaklaster.ru",
        "state-history-museum-tula": "tula.shm.ru",
        "nimfozorium-tula": "tiam-tula.ru",
        "tula-exotarium": "tulazoo.ru",
    }
    for slug, expected_host in hosts.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert urlparse(place.source.url).hostname == expected_host


def test_tula_search_free_and_family_are_city_scoped() -> None:
    city = catalog()
    assert city.search_places("самовары")[0].slug == "tula-samovars-museum"
    assert city.search_places("экзотариум")[0].slug == "tula-exotarium"
    free = city.places_for_category("free")
    family = {p.slug for p in city.places_for_category("family")}
    assert len(free) >= 16 and all(p.is_free for p in free)
    assert {
        "tula-exotarium", "tula-kremlin", "kazanskaya-embankment-tula",
        "belousov-central-park", "oktava-cluster", "tula-antiquities",
    } <= family


def test_tula_routes_refer_to_known_unique_stops_and_cover_scenarios() -> None:
    city = catalog()
    routes = {r.slug: r for r in city.routes}
    assert {
        "tula-first-visit", "tula-arms-demidovs", "tula-museum-quarter",
        "tula-family", "tula-industry", "tula-culture-literature",
        "tula-central-parks", "tula-zarechye-parks",
    } <= routes.keys()
    assert "tula-weapons-helmet" in routes["tula-arms-demidovs"].place_slugs
    assert "tula-exotarium" in routes["tula-family"].place_slugs
    assert "tula-machine-museum" in routes["tula-industry"].place_slugs
    assert "state-history-museum-tula" in routes["tula-museum-quarter"].place_slugs
    known = {place.slug for place in city.places}
    for route in city.routes:
        assert len(route.place_slugs) == len(set(route.place_slugs))
        assert set(route.place_slugs) <= known
        assert route.duration_minutes > 0 and route.distance_km > 0


def test_tula_restricted_access_is_not_promised() -> None:
    city = catalog()
    demidov = city.place_by_slug("tula-demidov-museum")
    church = city.place_by_slug("nikolo-zaretsky-church")
    old_arms = city.place_by_slug("kremlin-epiphany-cathedral")
    assert demidov is not None and church is not None and old_arms is not None
    assert "не гарантирован" in demidov.summary
    assert "внешний осмотр" in church.summary
    assert "внешний осмотр" in old_arms.summary

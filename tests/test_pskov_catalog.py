from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog

CITY_SLUG = "pskov"


def catalog():
    return get_catalog(CITY_SLUG)


def test_pskov_full_city_catalog_and_sources() -> None:
    city = catalog()
    assert len(city.places) >= 35
    assert len(city.routes) >= 9
    assert len({p.district for p in city.places}) >= 9
    for place in city.places:
        assert 57.79 <= place.latitude <= 57.85
        assert 28.25 <= place.longitude <= 28.38
        assert place.source.checked_at == date(2026, 10, 8)
        parsed = urlparse(place.source.url)
        assert parsed.scheme == "https" and parsed.hostname


def test_pskov_official_museum_and_unesco_provenance() -> None:
    city = catalog()
    official_hosts = {
        "pskov-krom": "museumpskov.ru",
        "prikaz-chambers": "museumpskov.ru",
        "pogankin-chambers": "museumpskov.ru",
        "postnikov-yard": "www.culture.ru",
        "magic-hill-park": "magic-hill.ru",
        "mirozhsky-cathedral": "whc.unesco.org",
        "snetogorsk-monastery": "whc.unesco.org",
        "john-baptist-cathedral": "whc.unesco.org",
        "basil-hill": "www.hramnagorke.ru",
    }
    for slug, host in official_hosts.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert urlparse(place.source.url).hostname == host


def test_pskov_family_free_and_search() -> None:
    city = catalog()
    assert city.search_places("Поганкины палаты")[0].slug == "pogankin-chambers"
    assert city.search_places("Парк Куопио")[0].slug == "kuopio-park"
    assert {p.slug for p in city.places_for_category("family")} >= {
        "pskov-krom", "olga-chapel", "pskov-arboretum",
        "kuopio-park", "postnikov-yard", "magic-hill-park",
    }
    free = city.places_for_category("free")
    assert len(free) >= 21
    assert all(p.is_free for p in free)


def test_pskov_routes_reference_known_city_places() -> None:
    city = catalog()
    routes = {r.slug: r for r in city.routes}
    assert {
        "pskov-first-day", "pskov-kremlin-fortress", "pskov-unesco-south",
        "pskov-unesco-north", "pskov-museum-day", "pskov-family-day",
        "pskov-rivers", "pskov-mirozhsky-gardens", "pskov-north-monastery",
    } <= routes.keys()
    assert "mirozhsky-cathedral" in routes["pskov-unesco-south"].place_slugs
    assert "snetogorsk-monastery" in routes["pskov-north-monastery"].place_slugs
    assert "pogankin-chambers" in routes["pskov-museum-day"].place_slugs
    known = {p.slug for p in city.places}
    for route in city.routes:
        assert route.duration_minutes > 0 and route.distance_km > 0
        assert set(route.place_slugs) <= known
        assert len(route.place_slugs) == len(set(route.place_slugs))


def test_pskov_restricted_access_is_explicit() -> None:
    city = catalog()
    pogankin = city.place_by_slug("pogankin-chambers")
    mirozh = city.place_by_slug("mirozhsky-cathedral")
    vlasev = city.place_by_slug("vlasevskaya-tower")
    assert pogankin is not None and mirozh is not None and vlasev is not None
    assert "временно закрываться" in pogankin.summary
    assert "режима объекта" in mirozh.summary
    assert "музейному режиму" in vlasev.summary

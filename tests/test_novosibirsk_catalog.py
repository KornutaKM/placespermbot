from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog


def test_novosibirsk_expanded_city_museum_park_coverage() -> None:
    city = get_catalog("novosibirsk")
    assert len(city.places) >= 33
    assert len(city.routes) >= 13
    assert len({p.category for p in city.places}) == 5
    assert len({p.district for p in city.places}) >= 12
    assert sum(p.category == "museums" for p in city.places) >= 9
    for slug, host in {
        "nsk-nature-museum": "www.en.youmuseum.ru",
        "nsk-novo-nikolaevsk-estate": "www.culture.ru",
        "nsk-sun-museum": "museumofsun.ru",
        "nsk-kikina-planetarium": "www.nebo-nsk.ru",
        "nsk-pervomaisky-garden": "www.novo-sibirsk.ru",
    }.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert place.source.checked_at == date(2026, 10, 8)
        assert urlparse(place.source.url).hostname == host


def test_novosibirsk_family_history_and_remote_route_safety() -> None:
    city = get_catalog("novosibirsk")
    assert city.search_places("Музей Солнца")[0].slug == "nsk-sun-museum"
    assert city.search_places("Берёзовая роща")[0].slug == "nsk-birch-grove"
    family = {p.slug for p in city.places_for_category("family")}
    free = {p.slug for p in city.places_for_category("free")}
    assert "nsk-kikina-planetarium" in family
    assert "nsk-kikina-planetarium" not in free
    assert "nsk-park-gorodskoye-nachalo" in free
    assert "nsk-sun-museum" not in free
    route = city.route_by_slug("nsk-cosmology")
    assert route is not None and "nsk-kikina-planetarium" in route.place_slugs
    route = city.route_by_slug("nsk-scientific-neighborhood")
    assert route is not None and "akademgorodok-nsk" in route.place_slugs
    assert all(len(r.place_slugs) >= 2 for r in city.routes)

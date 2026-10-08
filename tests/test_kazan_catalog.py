from datetime import date
from urllib.parse import urlparse

from app.catalog import get_catalog


def test_kazan_expanded_city_profile_and_provenance() -> None:
    city = get_catalog("kazan")
    assert len(city.places) >= 28
    assert len(city.routes) >= 10
    assert len({place.category for place in city.places}) >= 5
    assert len({place.district for place in city.places}) >= 9
    assert sum(place.category == "museums" for place in city.places) >= 8
    for slug in (
        "kaz-islamic-culture-museum",
        "kaz-tukay-literary-museum",
        "kaz-kayum-nasyri-museum",
        "kaz-white-flowers-boulevard",
        "kaz-family-center-observation",
    ):
        place = city.place_by_slug(slug)
        assert place is not None
        assert place.source.checked_at == date(2026, 10, 8)
        assert urlparse(place.source.url).hostname == "go.kzn.ru"
        assert 55.74 <= place.latitude <= 55.86
        assert 49.03 <= place.longitude <= 49.19


def test_kazan_search_virtual_categories_and_routes() -> None:
    city = get_catalog("kazan")
    assert city.search_places("Музей Каюма Насыри")[0].slug == "kaz-kayum-nasyri-museum"
    assert city.search_places("Белые цветы")[0].slug == "kaz-white-flowers-boulevard"
    free = {place.slug for place in city.places_for_category("free")}
    family = {place.slug for place in city.places_for_category("family")}
    assert "kaz-victory-park" in free
    assert "kaz-tugan-avylym" in family
    assert "kaz-islamic-culture-museum" not in free
    assert "kaz-family-center-observation" not in free
    routes = {route.slug: route for route in city.routes}
    assert "kaz-literary-heritage" in routes
    assert "kaz-victory-family" in routes
    assert "kaz-islamic-culture-museum" in routes["kaz-museum-heritage"].place_slugs
    assert len(routes["kazan-family-north"].place_slugs) >= 3
    assert all(len(route.place_slugs) >= 2 for route in city.routes)

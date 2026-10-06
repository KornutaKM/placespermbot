from dataclasses import dataclass

from app.catalog import get_catalog, list_catalogs
from app.catalog_validation import validate_catalogs

EXPECTED_CITIES = {
    "kaliningrad": "Калининград",
    "kazan": "Казань",
    "moscow": "Москва",
    "nizhny-novgorod": "Нижний Новгород",
    "novosibirsk": "Новосибирск",
    "perm": "Пермь",
    "saint-petersburg": "Санкт-Петербург",
    "sochi": "Сочи",
    "vladivostok": "Владивосток",
    "volgograd": "Волгоград",
    "yaroslavl": "Ярославль",
    "yekaterinburg": "Екатеринбург",
}


@dataclass(frozen=True)
class CatalogQualityProfile:
    min_places: int
    min_routes: int
    min_districts: int
    min_categories: int
    min_free_places: int
    min_family_places: int
    min_museums: int


CITY_QUALITY = {
    "kaliningrad": CatalogQualityProfile(14, 5, 3, 3, 5, 2, 4),
    "kazan": CatalogQualityProfile(14, 5, 3, 3, 5, 4, 2),
    "moscow": CatalogQualityProfile(18, 8, 8, 4, 8, 5, 3),
    "nizhny-novgorod": CatalogQualityProfile(15, 6, 3, 3, 8, 2, 3),
    "novosibirsk": CatalogQualityProfile(14, 6, 6, 4, 7, 4, 4),
    "perm": CatalogQualityProfile(19, 7, 5, 5, 8, 5, 6),
    "saint-petersburg": CatalogQualityProfile(20, 6, 5, 4, 7, 4, 7),
    "sochi": CatalogQualityProfile(14, 5, 3, 4, 6, 4, 2),
    "vladivostok": CatalogQualityProfile(18, 7, 6, 5, 10, 6, 5),
    "volgograd": CatalogQualityProfile(19, 7, 5, 5, 12, 8, 5),
    "yaroslavl": CatalogQualityProfile(14, 5, 2, 3, 7, 3, 4),
    "yekaterinburg": CatalogQualityProfile(15, 7, 4, 5, 7, 2, 5),
}


def test_all_supported_cities_are_registered() -> None:
    catalogs = {catalog.slug: catalog for catalog in list_catalogs()}
    assert {slug: catalog.name for slug, catalog in catalogs.items()} == EXPECTED_CITIES
    assert CITY_QUALITY.keys() == EXPECTED_CITIES.keys()


def test_catalogs_meet_city_quality_profiles() -> None:
    for city_slug, profile in CITY_QUALITY.items():
        catalog = get_catalog(city_slug)

        assert len(catalog.places) >= profile.min_places, city_slug
        assert len(catalog.routes) >= profile.min_routes, city_slug
        assert len({place.district for place in catalog.places}) >= profile.min_districts, city_slug
        assert len({place.category for place in catalog.places}) >= profile.min_categories, city_slug
        assert sum(place.is_free for place in catalog.places) >= profile.min_free_places, city_slug
        assert sum("с детьми" in place.tags for place in catalog.places) >= profile.min_family_places, city_slug
        assert sum(place.category == "museums" for place in catalog.places) >= profile.min_museums, city_slug


def test_routes_are_valid_and_use_unique_places() -> None:
    for city_slug in EXPECTED_CITIES:
        catalog = get_catalog(city_slug)
        place_slugs = [place.slug for place in catalog.places]

        assert len(place_slugs) == len(set(place_slugs))
        assert all(place.visit_minutes > 0 for place in catalog.places)
        assert all(-90 <= place.latitude <= 90 for place in catalog.places)
        assert all(-180 <= place.longitude <= 180 for place in catalog.places)

        known = set(place_slugs)
        route_slugs = [route.slug for route in catalog.routes]
        assert len(route_slugs) == len(set(route_slugs))
        for route in catalog.routes:
            assert route.place_slugs
            assert set(route.place_slugs) <= known
            assert len(route.place_slugs) == len(set(route.place_slugs))
            assert route.duration_minutes > 0
            assert route.distance_km > 0


def test_city_search_is_isolated_between_catalogs() -> None:
    kazan = get_catalog("kazan")
    nizhny = get_catalog("nizhny-novgorod")

    assert kazan.place_by_slug("kazan-kremlin") is not None
    assert kazan.place_by_slug("nizhny-kremlin") is None
    assert nizhny.place_by_slug("nizhny-kremlin") is not None
    assert nizhny.place_by_slug("kazan-kremlin") is None
    assert kazan.search_places("Кремль")[0].slug == "kazan-kremlin"
    assert nizhny.search_places("Кремль")[0].slug == "nizhny-kremlin"


def test_all_catalogs_pass_reusable_validation() -> None:
    assert validate_catalogs(list_catalogs()) == ()

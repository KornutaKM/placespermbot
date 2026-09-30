from app.catalog import get_catalog, list_catalogs


EXPECTED_CITIES = {
    "kaliningrad": "Калининград",
    "kazan": "Казань",
    "moscow": "Москва",
    "nizhny-novgorod": "Нижний Новгород",
    "novosibirsk": "Новосибирск",
    "perm": "Пермь",
    "saint-petersburg": "Санкт-Петербург",
    "yekaterinburg": "Екатеринбург",
}


def test_all_supported_cities_are_registered() -> None:
    catalogs = {catalog.slug: catalog for catalog in list_catalogs()}

    assert {slug: catalog.name for slug, catalog in catalogs.items()} == EXPECTED_CITIES


def test_new_city_catalogs_have_valid_routes_and_unique_places() -> None:
    for city_slug in EXPECTED_CITIES:
        catalog = get_catalog(city_slug)
        place_slugs = [place.slug for place in catalog.places]

        assert len(catalog.places) >= 5
        assert len(catalog.routes) >= 2
        assert len(place_slugs) == len(set(place_slugs))
        assert all(place.visit_minutes > 0 for place in catalog.places)
        assert all(-90 <= place.latitude <= 90 for place in catalog.places)
        assert all(-180 <= place.longitude <= 180 for place in catalog.places)

        known = set(place_slugs)
        for route in catalog.routes:
            assert route.place_slugs
            assert set(route.place_slugs) <= known
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


def test_large_new_city_catalogs_have_enough_discovery_depth() -> None:
    for city_slug in ("kaliningrad", "moscow", "novosibirsk", "yekaterinburg"):
        catalog = get_catalog(city_slug)

        assert len(catalog.places) >= 8
        assert len(catalog.routes) >= 3
        assert len({place.category for place in catalog.places}) >= 3
        assert sum(place.is_free for place in catalog.places) >= 5


def test_core_city_catalogs_have_richer_discovery_depth() -> None:
    for city_slug in ("kazan", "moscow", "nizhny-novgorod", "yekaterinburg"):
        catalog = get_catalog(city_slug)

        assert len(catalog.places) >= 12
        assert len(catalog.routes) >= 4
        assert len({place.category for place in catalog.places}) >= 3

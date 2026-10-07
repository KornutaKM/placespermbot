from importlib import import_module
from pkgutil import iter_modules

from app import data as data_package
from app.catalog import get_catalog, list_catalogs
from app.catalog_quality import validate_catalog_quality
from app.catalog_validation import validate_catalogs
from app.city_manifest import list_city_manifests


def test_all_city_data_modules_are_declared_in_manifest() -> None:
    discovered = set()
    for module_info in iter_modules(data_package.__path__):
        module = import_module(f"{data_package.__name__}.{module_info.name}")
        city_slug = getattr(module, "CITY_SLUG", None)
        if city_slug is not None:
            discovered.add(city_slug)

    declared = {manifest.slug for manifest in list_city_manifests()}

    assert declared == discovered


def test_all_manifest_cities_are_registered() -> None:
    manifests = {manifest.slug: manifest for manifest in list_city_manifests()}
    catalogs = {catalog.slug: catalog for catalog in list_catalogs()}

    assert catalogs.keys() == manifests.keys()
    assert {
        slug: catalog.name for slug, catalog in catalogs.items()
    } == {
        slug: manifest.name for slug, manifest in manifests.items()
    }


def test_catalogs_meet_manifest_quality_profiles() -> None:
    for manifest in list_city_manifests():
        catalog = get_catalog(manifest.slug)

        assert validate_catalog_quality(catalog, manifest.quality) == ()


def test_routes_are_valid_and_use_unique_places() -> None:
    for catalog in list_catalogs():
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

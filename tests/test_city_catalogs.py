from app.catalog import get_catalog, list_catalogs
from app.catalog_validation import validate_catalogs
from app.city_manifest import discover_city_definitions


def test_all_discovered_cities_are_registered() -> None:
    definitions = discover_city_definitions()
    catalogs = {catalog.slug: catalog for catalog in list_catalogs()}

    assert len(definitions) >= 19
    assert len(catalogs) == len(definitions)
    assert {definition.slug: definition.name for definition in definitions} == {
        slug: catalog.name for slug, catalog in catalogs.items()
    }


def test_catalogs_meet_city_owned_quality_profiles() -> None:
    for definition in discover_city_definitions():
        profile = definition.quality
        catalog = get_catalog(definition.slug)

        assert min(
            profile.min_places,
            profile.min_routes,
            profile.min_districts,
            profile.min_categories,
            profile.min_free_places,
            profile.min_family_places,
            profile.min_museums,
        ) > 0, definition.slug
        assert len(catalog.places) >= profile.min_places, definition.slug
        assert len(catalog.routes) >= profile.min_routes, definition.slug
        assert (
            len({place.district for place in catalog.places})
            >= profile.min_districts
        ), definition.slug
        assert (
            len({place.category for place in catalog.places})
            >= profile.min_categories
        ), definition.slug
        assert (
            sum(place.is_free for place in catalog.places)
            >= profile.min_free_places
        ), definition.slug
        assert (
            sum("с детьми" in place.tags for place in catalog.places)
            >= profile.min_family_places
        ), definition.slug
        assert (
            sum(place.category == "museums" for place in catalog.places)
            >= profile.min_museums
        ), definition.slug


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

"""New urban catalogs must work throughout the bot and Mini App infrastructure."""

from itertools import pairwise

from fastapi.testclient import TestClient

from app.catalog import distance_km, get_catalog, has_catalog, list_catalogs
from app.catalog_coverage import assess_catalog_coverage
from app.catalog_quality import validate_catalog_quality
from app.catalog_validation import validate_catalog
from app.city_manifest import list_city_manifests
from app.config import Settings
from app.data.osm_seed_2026 import OSM_SEED_CITIES
from app.data.wikidata_seed_2026 import WIKIDATA_SEED_CITIES
from app.miniapp_route_builder import RouteBuildRequest, build_miniapp_route
from app.miniapp_server import create_miniapp
from app.route_review import hard_route_findings, inspect_routes

NEW_CITY_SLUGS = (
    "suzdal", "pyatigorsk", "kislovodsk", "derbent", "penza",
    "astrakhan", "yoshkar-ola", "ulan-ude", "syktyvkar", "kursk",
)


def test_ten_new_cities_have_genuine_places_and_itineraries():
    catalogs = list_catalogs()
    assert len(catalogs) == 45 + len(OSM_SEED_CITIES) + len(WIKIDATA_SEED_CITIES)
    assert len({city.slug for city in catalogs}) == 45 + len(OSM_SEED_CITIES) + len(WIKIDATA_SEED_CITIES)
    manifests = {item.slug: item for item in list_city_manifests()}
    for slug in NEW_CITY_SLUGS:
        assert has_catalog(slug)
        catalog = get_catalog(slug)
        assert len(catalog.places) == 12
        assert len(catalog.routes) == 5
        assert not validate_catalog(catalog)
        assert not validate_catalog_quality(catalog, manifests[slug].quality)
        assert not hard_route_findings(inspect_routes(catalog))
        assert len({place.slug for place in catalog.places}) == 12
        assert all(place.source.url.startswith("https://") for place in catalog.places)
        assert len({place.district for place in catalog.places}) >= 5
        assert sum(place.is_free for place in catalog.places) >= 5
        assert sum(place.category == "museums" for place in catalog.places) >= 2
        for route in catalog.routes:
            assert len(route.place_slugs) >= 2
            assert len(route.place_slugs) == len(set(route.place_slugs))
            ordered = tuple(catalog.place_by_slug(item) for item in route.place_slugs)
            assert all(ordered)
            assert route.duration_minutes >= sum(p.visit_minutes for p in ordered)
            assert route.distance_km > 0
        assert assess_catalog_coverage(catalog).places == 12
        assert catalog.search_places(catalog.places[0].title)


def test_expanded_cities_support_all_seven_planner_modes_without_fake_routes():
    interests = (
        "classic", "museums", "architecture", "walks",
        "unusual", "family", "free",
    )
    for slug in NEW_CITY_SLUGS:
        catalog = get_catalog(slug)
        for interest in interests:
            route = build_miniapp_route(
                catalog,
                RouteBuildRequest(interest=interest, budget_minutes=360),
            )
            # Thin starter categories may have no route, but must never fabricate.
            if route is None:
                continue
            assert route.estimated_minutes <= 360
            assert {p.slug for p in route.places}.issubset(
                {p.slug for p in catalog.places}
            )
            assert all(
                distance_km(left, right) <= 5.0
                for left, right in pairwise(route.places)
            )


def test_new_city_catalogs_are_available_in_public_miniapp_api(tmp_path):
    with TestClient(create_miniapp(Settings(
        bot_token="123456789:expanded-cities-tests",
        database_path=str(tmp_path / "catalogs.db"),
        environment="development",
    ))) as client:
        cities = client.get("/api/cities")
        assert cities.status_code == 200
        assert len(cities.json()["cities"]) == 45 + len(OSM_SEED_CITIES) + len(WIKIDATA_SEED_CITIES)
        assert set(NEW_CITY_SLUGS).issubset(
            {item["slug"] for item in cities.json()["cities"]}
        )
        for slug in NEW_CITY_SLUGS:
            response = client.get("/api/catalogs/" + slug)
            assert response.status_code == 200
            payload = response.json()
            assert len(payload["places"]) == 12
            assert len(payload["routes"]) == 5
            assert payload["places"][0]["map_url"].startswith("https://")


def test_kursk_operator_sources_and_gallery_geolocation_are_documented():
    from datetime import date

    from app.place_evidence import public_evidence

    city = get_catalog("kursk")
    sources = {
        "kursk-deineka": "https://deinekagallery.ru/posetitelyam/",
        "kursk-museum-local": (
            "https://kursk-museum.ru/ekskursiya-kurskij-detinec/"
        ),
        "kursk-znamensky": "https://kursk-znamen-1.cerkov.ru/",
        "kursk-sergiev": "https://serge-kazan.cerkov.ru/",
    }
    for slug, url in sources.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert place.source.url == url
        assert place.source.checked_at == date(2026, 10, 11)
        evidence = public_evidence("kursk", slug, as_of=date(2026, 10, 11))
        assert evidence["status"] == "operator_listed"
        assert evidence["evidence_url"] == url
        assert "уточняйте" in evidence["finding"]

    gallery = city.place_by_slug("kursk-deineka")
    assert gallery.title == "Выставочный зал галереи имени А. А. Дейнеки"
    assert gallery.latitude == 51.745951
    assert gallery.longitude == 36.190608
    assert gallery.district == "Радищева, 85"
    assert "Советской, 3" in gallery.summary
    assert "Луначарского, 6" in city.place_by_slug(
        "kursk-museum-local"
    ).summary
    assert city.place_by_slug("kursk-red-square").source.url == (
        "https://www.culture.ru/s/kursk/"
    )
    assert "kursk-deineka" in city.route_by_slug(
        "kursk-museums"
    ).place_slugs
    assert not hard_route_findings(inspect_routes(city))


def test_kursk_archaeology_and_theatre_map_pins_match_named_city_venues():
    from datetime import date

    from app.place_evidence import public_evidence
    from app.place_freshness import build_inventory

    city = get_catalog("kursk")
    museum = city.place_by_slug("kursk-archaeology")
    theatre = city.place_by_slug("kursk-pushkin")
    assert museum is not None and theatre is not None
    assert (museum.latitude, museum.longitude) == (51.72053, 36.18591)
    assert museum.district == "Пионеров, 6"
    assert "Пионеров, 6" in museum.summary
    assert museum.source.url == (
        "https://welcomekursk.ru/places/485/"
        "kurskii-gosudarstvennyi-oblastnoi-muzei-arkheologii"
    )
    assert (theatre.latitude, theatre.longitude) == (51.739, 36.19163)
    assert theatre.district == "Ленина, 26"
    assert theatre.source.url == "https://kurskdrama.ru/kontakty/"
    evidence = public_evidence("kursk", "kursk-pushkin",
                               as_of=date(2026, 10, 11))
    assert evidence["status"] == "operator_listed"
    assert "уточняйте" in evidence["finding"]
    assert public_evidence("kursk", "kursk-archaeology",
                           as_of=date(2026, 10, 11))["status"] == (
        "not_independently_checked"
    )
    history = build_inventory(as_of=date(2026, 10, 11))
    record = next(
        row for row in history["places"]
        if (row["city_slug"], row["place_slug"]) ==
        ("kursk", "kursk-archaeology")
    )
    assert record["past_published_observation"]["reported_on"] == "2026-08-14"
    assert record["review_status"] == "requires_current_independent_confirmation"
    assert "kursk-archaeology" in city.route_by_slug(
        "kursk-museums"
    ).place_slugs
    assert "kursk-pushkin" in city.route_by_slug("kursk-historic").place_slugs
    assert not hard_route_findings(inspect_routes(city))

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
    museum = city.place_by_slug("kursk-museum-local")
    assert museum is not None
    assert museum.source.url == (
        "https://xn--46-6kc3bf4angc2g.xn--p1ai/organizations/"
        "обук-курский-областной-краеведческ/"
    )
    assert public_evidence(
        "kursk", "kursk-museum-local", as_of=date(2026, 10, 11)
    )["status"] == "not_independently_checked"
    assert city.place_by_slug("kursk-red-square").source.url == (
        "https://bitva.kursk.ru/routes/"
        "marshrut-po-severnomu-fasu-kurskoy-dugi/"
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
    assert city.place_by_slug("kursk-pushkin") is not None
    assert not hard_route_findings(inspect_routes(city))


def test_kursk_memorial_alley_identity_and_dated_public_space_caveats():
    city = get_catalog("kursk")
    memorial = city.place_by_slug("kursk-pobeda")
    alley = city.place_by_slug("kursk-heroes")
    garden = city.place_by_slug("kursk-city-garden")
    pioneers = city.place_by_slug("kursk-park-pioneers")
    street = city.place_by_slug("kursk-street-lenin")
    square = city.place_by_slug("kursk-red-square")
    assert all((memorial, alley, garden, pioneers, street, square))
    memorial_url = (
        "https://bitva.kursk.ru/routes/"
        "peshekhodnaya-ekskursiya-po-memorialnomu-kompleksu-kurskaya-duga/"
    )
    assert memorial.source.url == alley.source.url == memorial_url
    assert alley.title == "Аллея военной техники мемориала «Курская дуга»"
    assert "проектируемой Аллеей Героев" in alley.summary
    assert "24 сентября 2026" in pioneers.summary
    assert "временном ограничении" in pioneers.summary
    assert pioneers.source.url == "https://gi-kursk.ru/news/city/92519/"
    assert "октябре 2026" in garden.summary
    assert "может быть ограничена" in garden.summary
    assert "утверждён проект" in street.summary
    assert "не доказывает начала работ" in street.summary
    assert square.source.url == (
        "https://bitva.kursk.ru/routes/"
        "marshrut-po-severnomu-fasu-kurskoy-dugi/"
    )
    assert all(p.source.url != "https://www.culture.ru/s/kursk/"
               for p in city.places)
    assert alley.source.url != street.source.url
    assert "kursk-heroes" in {p.slug for p in city.places}
    assert "kursk-heroes" in city.route_by_slug("kursk-walk").place_slugs
    assert not hard_route_findings(inspect_routes(city))


def test_syktyvkar_operator_entrances_replace_generic_map_pins():
    from datetime import date

    from app.place_evidence import public_evidence

    city = get_catalog("syktyvkar")
    institutions = {
        "syktyvkar-national-museum": (
            "https://museumkomi.ru/?page_id=1609",
            61.6695, 50.8382, "Коммунистическая, 6",
        ),
        "syktyvkar-national-gallery": (
            "https://ngrkomi-art.ru/",
            61.6696, 50.8426, "Кирова, 44",
        ),
        "syktyvkar-savin": (
            "https://komidrama.ru/contacts",
            61.669566, 50.825026, "Первомайская, 56",
        ),
        "syktyvkar-opera": (
            "https://komiopera.ru/kontakty/",
            61.666167, 50.819313, "Коммунистическая, 32",
        ),
        "syktyvkar-geology": (
            "https://geo.komisc.ru/museum/museum-contacts",
            61.670871, 50.823662, "Первомайская, 54",
        ),
    }
    for slug, (url, lat, lon, address) in institutions.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert place.source.url == url
        assert place.source.checked_at == date(2026, 10, 11)
        assert place.latitude == lat and place.longitude == lon
        assert place.district == address
        evidence = public_evidence(
            "syktyvkar", slug, as_of=date(2026, 10, 11)
        )
        assert evidence["status"] == "operator_listed"
        assert evidence["evidence_url"] == url
    museum = city.place_by_slug("syktyvkar-national-museum")
    assert "Отдел природы" in museum.title
    assert "Отдел истории" in museum.summary
    assert "закрытым на капитальный ремонт" in museum.summary
    assert "предварительной записи" in city.place_by_slug(
        "syktyvkar-geology"
    ).summary
    assert city.place_by_slug("syktyvkar-stefan-square").source.url == (
        "https://tourism.rkomi.ru/about/cities/syktyvkar"
    )
    assert "syktyvkar-geology" in city.route_by_slug(
        "syktyvkar-museums"
    ).place_slugs
    assert not hard_route_findings(inspect_routes(city))


def test_syktyvkar_cathedral_and_two_monuments_have_safe_grounded_pins():
    from datetime import date

    from app.place_evidence import public_evidence

    city = get_catalog("syktyvkar")
    cathedral = city.place_by_slug("syktyvkar-cathedral")
    kuratov = city.place_by_slug("syktyvkar-kurator")
    stefan = city.place_by_slug("syktyvkar-stefan-monument")
    assert cathedral is not None and kuratov is not None and stefan is not None
    assert (cathedral.latitude, cathedral.longitude) == (61.677794, 50.831536)
    assert cathedral.district == "Свободы, 60"
    assert cathedral.source.url == (
        "https://syktyvkar-eparchia.ru/index/"
        "prikhoda_svjato_stefanovskogo_kafedralnogo_sobora/0-24"
    )
    evidence = public_evidence(
        "syktyvkar", "syktyvkar-cathedral", as_of=date(2026, 10, 11)
    )
    assert evidence["status"] == "operator_listed"
    assert evidence["evidence_url"] == cathedral.source.url
    assert "уточняйте" in evidence["finding"]

    assert (kuratov.latitude, kuratov.longitude) == (61.665251, 50.820102)
    assert "Театральная площадь" == kuratov.district
    assert kuratov.source.url == (
        "https://tourism.rkomi.ru/travel-guide/pamyatnik-ia-kuratovu"
    )
    assert public_evidence(
        "syktyvkar", "syktyvkar-kurator", as_of=date(2026, 10, 11)
    )["status"] == "not_independently_checked"

    assert stefan.district == "Свободы, 60 — соборная территория"
    assert (stefan.latitude, stefan.longitude) == (
        cathedral.latitude, cathedral.longitude
    )
    assert "не подтверждённые координаты самой скульптуры" in stefan.summary
    assert stefan.source.url == (
        "https://tourism.rkomi.ru/travel-guide/pamyatnik-stefanu-permskomu"
    )
    assert public_evidence(
        "syktyvkar", "syktyvkar-stefan-monument", as_of=date(2026, 10, 11)
    )["status"] == "not_independently_checked"
    assert len(city.places) == 12 and len(city.routes) == 5
    assert not hard_route_findings(inspect_routes(city))


def test_syktyvkar_park_pin_is_not_confused_with_western_urban_square():
    city = get_catalog("syktyvkar")
    park = city.place_by_slug("syktyvkar-kirov-park")
    opera = city.place_by_slug("syktyvkar-opera")
    kuratov = city.place_by_slug("syktyvkar-kurator")
    assert park is not None and opera is not None and kuratov is not None
    assert park.title == "Парк имени С. М. Кирова"
    assert (park.latitude, park.longitude) == (61.6722, 50.8421)
    assert "ориентир внутри парка" in park.summary
    assert "не отдельный вход" in park.summary
    assert park.source.url == "https://drki-kirova21.ru/page/661"
    assert (opera.latitude, opera.longitude) == (61.666167, 50.819313)
    assert opera.source.url == "https://komiopera.ru/kontakty/"
    assert "режим кассы не равен" in opera.summary
    assert kuratov.source.url == (
        "https://tourism.rkomi.ru/travel-guide/pamyatnik-ia-kuratovu"
    )
    assert "реестровому описанию" in kuratov.summary
    assert "syktyvkar-kirov-park" in city.route_by_slug(
        "syktyvkar-walk"
    ).place_slugs
    assert not hard_route_findings(inspect_routes(city))


def test_ulan_ude_venues_have_true_operator_addresses_and_cautious_routes():
    from datetime import date

    from app.place_evidence import public_evidence

    city = get_catalog("ulan-ude")
    institutions = {
        "ulan-ude-opera": (
            "https://uuopera.ru/contacts/",
            51.8329, 107.5834, "Ленина, 51",
        ),
        "ulan-ude-history-museum": (
            "https://catalog.muzeyrb.ru/listing/"
            "музей-истории-бурятии-имени-м-н-хангал/",
            51.832009, 107.588356, "Профсоюзная, 29",
        ),
        "ulan-ude-art-museum": (
            "https://catalog.muzeyrb.ru/listing/художественный-музей/",
            51.825453, 107.589551, "Куйбышева, 29",
        ),
        "ulan-ude-ethnographic": (
            "https://xn--80akfjmebi8an4c6c.xn--p1ai/",
            51.8835, 107.6514, "Верхняя Берёзовка, 17б",
        ),
    }
    for slug, (url, lat, lon, address) in institutions.items():
        place = city.place_by_slug(slug)
        assert place is not None
        assert place.source.url == url
        assert place.source.checked_at == date(2026, 10, 11)
        assert place.latitude == lat and place.longitude == lon
        assert place.district == address
        evidence = public_evidence("ulan-ude", slug, as_of=date(2026, 10, 11))
        assert evidence["status"] == "operator_listed"
        assert evidence["evidence_url"] == url
        assert "уточняйте" in evidence["finding"]
    theatre = city.place_by_slug("ulan-ude-opera")
    history = city.place_by_slug("ulan-ude-history-museum")
    art = city.place_by_slug("ulan-ude-art-museum")
    ethno = city.place_by_slug("ulan-ude-ethnographic")
    assert "режим кассы" in theatre.summary.lower()
    assert "Хангалова" in history.title
    assert "Сампилова" in art.title
    assert "Точка ориентировочная" in ethno.summary
    assert "автобус № 37" in ethno.summary
    assert distance_km(art, ethno) > 7.0

    museum_route = city.route_by_slug("ulan-ude-museums")
    assert {"ulan-ude-history-museum", "ulan-ude-art-museum",
            "ulan-ude-ethnographic"}.issubset(museum_route.place_slugs)
    assert "нужен транспорт" in museum_route.summary
    assert "время пересадки" in museum_route.summary
    assert len(city.places) == 12 and len(city.routes) == 5
    assert not hard_route_findings(inspect_routes(city))

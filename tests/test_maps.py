from dataclasses import replace
from urllib.parse import parse_qs, urlparse

from app.catalog import get_catalog
from app.data.spb import CITY_SLUG
from app.maps import (
    google_maps_directions_to_place_url,
    google_maps_route_links,
    google_maps_route_urls,
)


def catalog():
    return get_catalog(CITY_SLUG)


def coordinate(place) -> str:
    return f"{place.latitude:.6f},{place.longitude:.6f}"


def test_single_place_uses_search_url() -> None:
    place = catalog().places[0]

    (url,) = google_maps_route_urls((place,))
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    assert parsed.path == "/maps/search/"
    assert query["api"] == ["1"]
    assert query["query"] == [coordinate(place)]


def test_two_places_use_walking_directions() -> None:
    places = catalog().places[:2]

    (url,) = google_maps_route_urls(places)
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    assert parsed.path == "/maps/dir/"
    assert query["origin"] == [coordinate(places[0])]
    assert query["destination"] == [coordinate(places[-1])]
    assert query["travelmode"] == ["walking"]
    assert "waypoints" not in query


def test_five_places_use_three_waypoints() -> None:
    places = catalog().places[:5]

    (url,) = google_maps_route_urls(places)
    query = parse_qs(urlparse(url).query)

    assert query["origin"] == [coordinate(places[0])]
    assert query["destination"] == [coordinate(places[4])]
    assert query["waypoints"] == [
        "|".join(coordinate(place) for place in places[1:4])
    ]


def test_long_route_is_split_into_overlapping_mobile_safe_segments() -> None:
    original = catalog().places[:6]
    places = tuple(
        replace(place, latitude=55.0, longitude=49.0 + index / 1000)
        for index, place in enumerate(original)
    )

    urls = google_maps_route_urls(places)

    assert len(urls) == 2

    first = parse_qs(urlparse(urls[0]).query)
    second = parse_qs(urlparse(urls[1]).query)

    assert first["origin"] == [coordinate(places[0])]
    assert first["destination"] == [coordinate(places[4])]
    assert second["origin"] == [coordinate(places[4])]
    assert second["destination"] == [coordinate(places[5])]


def test_empty_route_has_no_map_url() -> None:
    assert google_maps_route_urls(()) == ()


def test_directions_to_place_uses_device_origin_and_walking_navigation() -> None:
    place = catalog().places[0]

    url = google_maps_directions_to_place_url(place)
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    assert parsed.path == "/maps/dir/"
    assert query["api"] == ["1"]
    assert query["destination"] == [coordinate(place)]
    assert query["travelmode"] == ["walking"]
    assert query["dir_action"] == ["navigate"]
    assert "origin" not in query


def test_long_distant_leg_is_separate_transit_link_not_walking() -> None:
    catalog_moscow = get_catalog("moscow")
    route = catalog_moscow.route_by_slug("moscow-modern")
    assert route is not None
    places = tuple(catalog_moscow.place_by_slug(slug) for slug in route.place_slugs)
    assert all(place is not None for place in places)
    links = google_maps_route_links(places)
    assert len(links) == 1
    assert links[0].mode == "transit"
    query = parse_qs(urlparse(links[0].url).query)
    assert query["travelmode"] == ["transit"]
    assert query["origin"] == [coordinate(places[0])]
    assert query["destination"] == [coordinate(places[1])]


def test_mixed_trip_splits_walk_transit_walk_without_losing_stops() -> None:
    original = catalog().places[:4]
    latitudes = (55.0, 55.001, 55.25, 55.251)
    places = tuple(
        replace(place, latitude=lat, longitude=49.0)
        for place, lat in zip(original, latitudes)
    )
    links = google_maps_route_links(places)
    assert [link.mode for link in links] == ["walking", "transit", "walking"]
    assert [link.first_slug for link in links] == [
        places[0].slug, places[1].slug, places[2].slug
    ]
    assert [link.last_slug for link in links] == [
        places[1].slug, places[2].slug, places[3].slug
    ]
    assert [parse_qs(urlparse(link.url).query)["travelmode"][0] for link in links] == [
        "walking", "transit", "walking"
    ]
    assert google_maps_route_urls(places) == tuple(link.url for link in links)


def test_two_distant_jumps_make_two_separate_transit_links() -> None:
    original = catalog().places[:3]
    latitudes = (55.0, 55.25, 55.50)
    places = tuple(
        replace(place, latitude=lat, longitude=49.0)
        for place, lat in zip(original, latitudes)
    )
    links = google_maps_route_links(places)
    assert len(links) == 2
    assert [link.mode for link in links] == ["transit", "transit"]
    assert links[0].last_slug == links[1].first_slug


def test_every_long_editorial_leg_is_mode_aware() -> None:
    from app.catalog import list_catalogs
    from app.route_safety import route_geography

    long_routes = 0
    for city in list_catalogs():
        for route in city.routes:
            places = tuple(city.place_by_slug(slug) for slug in route.place_slugs)
            assert all(place is not None for place in places)
            geography = route_geography(places)
            if geography.long_legs:
                long_routes += 1
                links = google_maps_route_links(places)
                transit_edges = {
                    (link.first_slug, link.last_slug)
                    for link in links if link.mode == "transit"
                }
                assert all(
                    (first, second) in transit_edges
                    for first, second, _distance in geography.long_legs
                )
    assert long_routes > 0

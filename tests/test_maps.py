from urllib.parse import parse_qs, urlparse

from app.catalog import get_catalog
from app.data.spb import CITY_SLUG
from app.maps import google_maps_directions_to_place_url, google_maps_route_urls


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
    places = catalog().places[:6]

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

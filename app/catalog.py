from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

from app.data import spb
from app.domain import Place, RoutePlan


@dataclass(frozen=True, slots=True)
class CityCatalog:
    slug: str
    name: str
    category_labels: dict[str, str]
    places: tuple[Place, ...]
    routes: tuple[RoutePlan, ...]

    def place_by_slug(self, slug: str) -> Place | None:
        return next((place for place in self.places if place.slug == slug), None)

    def route_by_slug(self, slug: str) -> RoutePlan | None:
        return next((route for route in self.routes if route.slug == slug), None)

    def places_for_category(self, category: str) -> tuple[Place, ...]:
        if category == "free":
            return tuple(place for place in self.places if place.is_free)
        if category == "family":
            return tuple(place for place in self.places if "с детьми" in place.tags)
        return tuple(place for place in self.places if place.category == category)

    def search_places(self, query: str, *, limit: int = 8) -> tuple[Place, ...]:
        terms = tuple(part for part in _normalize(query).split() if part)
        if not terms:
            return ()

        ranked: list[tuple[int, Place]] = []
        for place in self.places:
            title = _normalize(place.title)
            tags = _normalize(" ".join(place.tags))
            district = _normalize(place.district)
            summary = _normalize(place.summary)

            score = 0
            for term in terms:
                if term in title:
                    score += 8
                if term in tags:
                    score += 5
                if term in district:
                    score += 3
                if term in summary:
                    score += 1

            if score:
                ranked.append((score, place))

        ranked.sort(key=lambda item: (-item[0], item[1].title))
        return tuple(place for _, place in ranked[:limit])

    def nearby_places(
        self,
        origin_slug: str,
        *,
        radius_km: float = 3.0,
        limit: int = 5,
    ) -> tuple[tuple[Place, float], ...]:
        origin = self.place_by_slug(origin_slug)
        if origin is None:
            return ()

        ranked: list[tuple[Place, float]] = []
        for place in self.places:
            if place.slug == origin.slug:
                continue
            distance = distance_km(origin, place)
            if distance <= radius_km:
                ranked.append((place, distance))

        ranked.sort(key=lambda item: item[1])
        return tuple(ranked[:limit])

    def nearby_from_coordinates(
        self,
        latitude: float,
        longitude: float,
        *,
        radius_km: float = 10.0,
        limit: int = 8,
    ) -> tuple[tuple[Place, float], ...]:
        if radius_km <= 0 or limit <= 0:
            return ()

        ranked: list[tuple[Place, float]] = []
        for place in self.places:
            distance = coordinates_distance_km(
                latitude,
                longitude,
                place.latitude,
                place.longitude,
            )
            if distance <= radius_km:
                ranked.append((place, distance))

        ranked.sort(key=lambda item: (item[1], item[0].title))
        return tuple(ranked[:limit])


def _normalize(value: str) -> str:
    return " ".join(value.casefold().replace("ё", "е").split())


def coordinates_distance_km(
    first_latitude: float,
    first_longitude: float,
    second_latitude: float,
    second_longitude: float,
) -> float:
    earth_radius_km = 6371.0088
    lat1 = radians(first_latitude)
    lat2 = radians(second_latitude)
    delta_lat = lat2 - lat1
    delta_lon = radians(second_longitude - first_longitude)

    haversine = (
        sin(delta_lat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
    )
    return 2 * earth_radius_km * asin(sqrt(haversine))


def distance_km(first: Place, second: Place) -> float:
    return coordinates_distance_km(
        first.latitude,
        first.longitude,
        second.latitude,
        second.longitude,
    )


_CATALOGS: dict[str, CityCatalog] = {
    spb.CITY_SLUG: CityCatalog(
        slug=spb.CITY_SLUG,
        name=spb.CITY_NAME,
        category_labels=spb.CATEGORY_LABELS,
        places=spb.PLACES,
        routes=spb.ROUTES,
    )
}


def get_catalog(city_slug: str) -> CityCatalog:
    try:
        return _CATALOGS[city_slug]
    except KeyError as exc:
        raise RuntimeError(f"Unsupported city: {city_slug}") from exc

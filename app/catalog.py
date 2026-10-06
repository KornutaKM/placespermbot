from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

from app.data import (
    kaliningrad,
    kazan,
    krasnoyarsk,
    moscow,
    nizhny_novgorod,
    novosibirsk,
    omsk,
    perm,
    rostov_on_don,
    samara,
    sochi,
    spb,
    ufa,
    vladivostok,
    volgograd,
    yaroslavl,
    yekaterinburg,
)
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
    sochi.CITY_SLUG: CityCatalog(
        slug=sochi.CITY_SLUG,
        name=sochi.CITY_NAME,
        category_labels=sochi.CATEGORY_LABELS,
        places=sochi.PLACES,
        routes=sochi.ROUTES,
    ),
    yaroslavl.CITY_SLUG: CityCatalog(
        slug=yaroslavl.CITY_SLUG,
        name=yaroslavl.CITY_NAME,
        category_labels=yaroslavl.CATEGORY_LABELS,
        places=yaroslavl.PLACES,
        routes=yaroslavl.ROUTES,
    ),
    kaliningrad.CITY_SLUG: CityCatalog(
        slug=kaliningrad.CITY_SLUG,
        name=kaliningrad.CITY_NAME,
        category_labels=kaliningrad.CATEGORY_LABELS,
        places=kaliningrad.PLACES,
        routes=kaliningrad.ROUTES,
    ),
    novosibirsk.CITY_SLUG: CityCatalog(
        slug=novosibirsk.CITY_SLUG,
        name=novosibirsk.CITY_NAME,
        category_labels=novosibirsk.CATEGORY_LABELS,
        places=novosibirsk.PLACES,
        routes=novosibirsk.ROUTES,
    ),
    omsk.CITY_SLUG: CityCatalog(
        slug=omsk.CITY_SLUG,
        name=omsk.CITY_NAME,
        category_labels=omsk.CATEGORY_LABELS,
        places=omsk.PLACES,
        routes=omsk.ROUTES,
    ),
    moscow.CITY_SLUG: CityCatalog(
        slug=moscow.CITY_SLUG,
        name=moscow.CITY_NAME,
        category_labels=moscow.CATEGORY_LABELS,
        places=moscow.PLACES,
        routes=moscow.ROUTES,
    ),
    yekaterinburg.CITY_SLUG: CityCatalog(
        slug=yekaterinburg.CITY_SLUG,
        name=yekaterinburg.CITY_NAME,
        category_labels=yekaterinburg.CATEGORY_LABELS,
        places=yekaterinburg.PLACES,
        routes=yekaterinburg.ROUTES,
    ),
    kazan.CITY_SLUG: CityCatalog(
        slug=kazan.CITY_SLUG,
        name=kazan.CITY_NAME,
        category_labels=kazan.CATEGORY_LABELS,
        places=kazan.PLACES,
        routes=kazan.ROUTES,
    ),
    krasnoyarsk.CITY_SLUG: CityCatalog(
        slug=krasnoyarsk.CITY_SLUG,
        name=krasnoyarsk.CITY_NAME,
        category_labels=krasnoyarsk.CATEGORY_LABELS,
        places=krasnoyarsk.PLACES,
        routes=krasnoyarsk.ROUTES,
    ),
    nizhny_novgorod.CITY_SLUG: CityCatalog(
        slug=nizhny_novgorod.CITY_SLUG,
        name=nizhny_novgorod.CITY_NAME,
        category_labels=nizhny_novgorod.CATEGORY_LABELS,
        places=nizhny_novgorod.PLACES,
        routes=nizhny_novgorod.ROUTES,
    ),
    perm.CITY_SLUG: CityCatalog(
        slug=perm.CITY_SLUG,
        name=perm.CITY_NAME,
        category_labels=perm.CATEGORY_LABELS,
        places=perm.PLACES,
        routes=perm.ROUTES,
    ),
    rostov_on_don.CITY_SLUG: CityCatalog(
        slug=rostov_on_don.CITY_SLUG,
        name=rostov_on_don.CITY_NAME,
        category_labels=rostov_on_don.CATEGORY_LABELS,
        places=rostov_on_don.PLACES,
        routes=rostov_on_don.ROUTES,
    ),
    samara.CITY_SLUG: CityCatalog(
        slug=samara.CITY_SLUG,
        name=samara.CITY_NAME,
        category_labels=samara.CATEGORY_LABELS,
        places=samara.PLACES,
        routes=samara.ROUTES,
    ),
    spb.CITY_SLUG: CityCatalog(
        slug=spb.CITY_SLUG,
        name=spb.CITY_NAME,
        category_labels=spb.CATEGORY_LABELS,
        places=spb.PLACES,
        routes=spb.ROUTES,
    ),
    ufa.CITY_SLUG: CityCatalog(
        slug=ufa.CITY_SLUG,
        name=ufa.CITY_NAME,
        category_labels=ufa.CATEGORY_LABELS,
        places=ufa.PLACES,
        routes=ufa.ROUTES,
    ),
    vladivostok.CITY_SLUG: CityCatalog(
        slug=vladivostok.CITY_SLUG,
        name=vladivostok.CITY_NAME,
        category_labels=vladivostok.CATEGORY_LABELS,
        places=vladivostok.PLACES,
        routes=vladivostok.ROUTES,
    ),
    volgograd.CITY_SLUG: CityCatalog(
        slug=volgograd.CITY_SLUG,
        name=volgograd.CITY_NAME,
        category_labels=volgograd.CATEGORY_LABELS,
        places=volgograd.PLACES,
        routes=volgograd.ROUTES,
    ),
}


def get_catalog(city_slug: str) -> CityCatalog:
    try:
        return _CATALOGS[city_slug]
    except KeyError as exc:
        raise RuntimeError(f"Unsupported city: {city_slug}") from exc


def list_catalogs() -> tuple[CityCatalog, ...]:
    return tuple(sorted(_CATALOGS.values(), key=lambda catalog: catalog.name))


def has_catalog(city_slug: str) -> bool:
    return city_slug in _CATALOGS

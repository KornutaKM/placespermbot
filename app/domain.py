from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Place:
    slug: str
    title: str
    category: str
    summary: str
    emoji: str
    district: str
    visit_minutes: int
    is_free: bool
    latitude: float
    longitude: float
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RoutePlan:
    slug: str
    title: str
    summary: str
    duration_minutes: int
    distance_km: float
    place_slugs: tuple[str, ...]

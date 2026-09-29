from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class PlaceSource:
    name: str
    url: str
    checked_at: date


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
    source: PlaceSource
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RoutePlan:
    slug: str
    title: str
    summary: str
    duration_minutes: int
    distance_km: float
    place_slugs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GeneratedRoute:
    interest: str
    budget_minutes: int
    estimated_minutes: int
    distance_km: float
    places: tuple[Place, ...]

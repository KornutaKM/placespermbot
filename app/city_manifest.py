from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pkgutil import iter_modules
from types import ModuleType

from app import data
from app.domain import Place, RoutePlan


@dataclass(frozen=True, slots=True)
class CatalogQualityProfile:
    min_places: int
    min_routes: int
    min_districts: int
    min_categories: int
    min_free_places: int
    min_family_places: int
    min_museums: int


@dataclass(frozen=True, slots=True)
class CityDefinition:
    slug: str
    name: str
    category_labels: dict[str, str]
    places: tuple[Place, ...]
    routes: tuple[RoutePlan, ...]
    quality: CatalogQualityProfile


def city_module_names() -> tuple[str, ...]:
    return tuple(
        sorted(
            module.name
            for module in iter_modules(data.__path__)
            if not module.name.startswith("_")
        )
    )


def city_definition_from_module(module: ModuleType) -> CityDefinition:
    definition = getattr(module, "CITY", None)
    if not isinstance(definition, CityDefinition):
        raise RuntimeError(
            f"{module.__name__} must export CITY as a CityDefinition"
        )
    return definition


def discover_city_definitions() -> tuple[CityDefinition, ...]:
    definitions: list[CityDefinition] = []
    modules_by_slug: dict[str, str] = {}

    for module_name in city_module_names():
        qualified_name = f"{data.__name__}.{module_name}"
        module = import_module(qualified_name)
        definition = city_definition_from_module(module)

        previous_module = modules_by_slug.get(definition.slug)
        if previous_module is not None:
            raise RuntimeError(
                "Duplicate city slug "
                f"{definition.slug}: {previous_module} and {qualified_name}"
            )
        modules_by_slug[definition.slug] = qualified_name
        definitions.append(definition)

    return tuple(definitions)

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib import import_module
from pkgutil import iter_modules
from types import ModuleType

from app import data as data_package
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
class CityManifest:
    slug: str
    name: str
    category_labels: dict[str, str]
    places: tuple[Place, ...]
    routes: tuple[RoutePlan, ...]
    quality: CatalogQualityProfile


def city_data_module_names() -> tuple[str, ...]:
    return tuple(
        sorted(
            module.name
            for module in iter_modules(data_package.__path__)
            if not module.name.startswith("_")
        )
    )


def city_manifest_from_module(module: ModuleType) -> CityManifest:
    quality = getattr(module, "QUALITY_PROFILE", None)
    if not isinstance(quality, CatalogQualityProfile):
        raise RuntimeError(
            f"{module.__name__} must export QUALITY_PROFILE "
            "as CatalogQualityProfile"
        )

    required_attributes = (
        "CITY_SLUG",
        "CITY_NAME",
        "CATEGORY_LABELS",
        "PLACES",
        "ROUTES",
    )
    missing = tuple(
        attribute
        for attribute in required_attributes
        if not hasattr(module, attribute)
    )
    if missing:
        raise RuntimeError(
            f"{module.__name__} is missing city manifest fields: "
            f"{', '.join(missing)}"
        )

    return CityManifest(
        slug=module.CITY_SLUG,
        name=module.CITY_NAME,
        category_labels=module.CATEGORY_LABELS,
        places=module.PLACES,
        routes=module.ROUTES,
        quality=quality,
    )


@lru_cache(maxsize=1)
def list_city_manifests() -> tuple[CityManifest, ...]:
    manifests: list[CityManifest] = []
    modules_by_slug: dict[str, str] = {}

    for module_name in city_data_module_names():
        qualified_name = f"{data_package.__name__}.{module_name}"
        module = import_module(qualified_name)
        manifest = city_manifest_from_module(module)

        previous_module = modules_by_slug.get(manifest.slug)
        if previous_module is not None:
            raise RuntimeError(
                "Duplicate city manifest slug "
                f"{manifest.slug}: {previous_module} and {qualified_name}"
            )
        modules_by_slug[manifest.slug] = qualified_name
        manifests.append(manifest)

    return tuple(manifests)

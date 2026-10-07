from types import ModuleType

import pytest

from app.city_manifest import (
    CatalogQualityProfile,
    city_data_module_names,
    city_manifest_from_module,
    list_city_manifests,
)


def test_all_city_data_modules_are_auto_discovered() -> None:
    module_names = city_data_module_names()
    manifests = list_city_manifests()

    assert len(module_names) >= 19
    assert len(manifests) == len(module_names)
    assert {"spb", "perm", "omsk", "chelyabinsk"} <= set(module_names)
    assert len({manifest.slug for manifest in manifests}) == len(manifests)


def test_city_module_without_quality_profile_fails_closed() -> None:
    module = ModuleType("app.data.broken_city")

    with pytest.raises(
        RuntimeError,
        match="must export QUALITY_PROFILE as CatalogQualityProfile",
    ):
        city_manifest_from_module(module)


def test_city_module_missing_required_fields_fails_closed() -> None:
    module = ModuleType("app.data.incomplete_city")
    module.QUALITY_PROFILE = CatalogQualityProfile(12, 4, 3, 3, 4, 2, 2)

    with pytest.raises(
        RuntimeError,
        match="is missing city manifest fields",
    ):
        city_manifest_from_module(module)

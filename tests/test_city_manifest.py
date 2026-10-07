from types import ModuleType

import pytest

from app.city_manifest import (
    CityDefinition,
    city_definition_from_module,
    city_module_names,
    discover_city_definitions,
)


def test_city_modules_are_discovered_without_central_registry() -> None:
    module_names = city_module_names()
    definitions = discover_city_definitions()

    assert len(module_names) >= 19
    assert len(definitions) == len(module_names)
    assert {"spb", "perm", "omsk", "chelyabinsk"} <= set(module_names)
    assert len({definition.slug for definition in definitions}) == len(definitions)


def test_every_discovered_city_exports_definition_and_quality_profile() -> None:
    for definition in discover_city_definitions():
        assert isinstance(definition, CityDefinition)
        assert definition.slug
        assert definition.name
        assert definition.places
        assert definition.routes
        assert definition.quality.min_places > 0
        assert definition.quality.min_routes > 0


def test_city_module_without_definition_fails_closed() -> None:
    module = ModuleType("app.data.broken_city")

    with pytest.raises(
        RuntimeError,
        match="must export CITY as a CityDefinition",
    ):
        city_definition_from_module(module)

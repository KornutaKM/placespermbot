"""Top-100 population coverage is real metadata, not fake empty city guides."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.catalog import list_catalogs
from app.config import Settings
from app.miniapp_server import create_miniapp
from app.top_city_coverage import (
    RANKING_DATE,
    RESERVED_SLUGS,
    TOP_100_NAMES,
    check_coverage_registry,
    coverage_summary,
    top_city_coverage,
)


def test_rank_and_coverage_contract():
    check_coverage_registry()
    ranked = top_city_coverage()
    assert len(TOP_100_NAMES) == len(ranked) == 100
    assert len({city.name for city in ranked}) == 100
    assert len({city.slug for city in ranked}) == 100
    assert [(city.rank, city.name) for city in ranked[:3]] == [
        (1, "Москва"), (2, "Санкт-Петербург"), (3, "Новосибирск")
    ]
    assert ranked[35].name == "Севастополь"
    assert ranked[55].name == "Симферополь"
    assert ranked[-1].name == "Абакан"
    assert RANKING_DATE == "2025-01-01"

    ready = [city for city in ranked if city.guide_available]
    pending = [city for city in ranked if not city.guide_available]
    assert len(ready) == 41
    assert len(pending) == 59
    assert len(list_catalogs()) == 45
    assert set(RESERVED_SLUGS) == {city.name for city in pending}
    for city in ready:
        catalog = next(c for c in list_catalogs() if c.slug == city.slug)
        assert catalog.name == city.name
        assert catalog.places and catalog.routes
    for city in pending:
        assert city.slug not in {c.slug for c in list_catalogs()}


def test_directory_api_is_public_but_pending_cities_are_not_catalogs():
    settings = Settings(
        bot_token="123456789:top100-tests",
        database_path=":memory:",
        environment="development",
        city_slug="perm",
    )
    with TestClient(create_miniapp(settings)) as client:
        response = client.get("/api/city-coverage")
        assert response.status_code == 200
        payload = response.json()
        assert payload == coverage_summary()
        assert payload["target_count"] == 100
        assert payload["ready_count"] == 41
        assert payload["pending_count"] == 59
        assert payload["catalog_city_count"] == 45
        assert payload["ranking_date"] == "2025-01-01"
        assert len(payload["ranking_sources"]) == 3
        assert "user_id" not in response.text
        assert "initData" not in response.text
        assert response.headers["cache-control"] == "no-store"

        # No fake empty catalogs or fallback places for cities awaiting curation.
        for name in ("Тольятти", "Севастополь", "Симферополь", "Абакан"):
            city = next(c for c in payload["cities"] if c["name"] == name)
            assert city["guide_available"] is False
            assert client.get(f"/api/catalogs/{city['slug']}").status_code == 404
        assert client.get("/api/catalogs/moscow").status_code == 200
        assert len(client.get("/api/cities").json()["cities"]) == 45


def test_city_can_be_promoted_only_by_real_manifest_registration(monkeypatch):
    import app.top_city_coverage as target

    original = target.list_city_manifests()
    monkeypatch.setattr(
        target, "list_city_manifests",
        lambda: (*original, SimpleNamespace(name="Тверь", slug="tver")),
    )
    summary = coverage_summary()
    assert (summary["ready_count"], summary["pending_count"]) == (42, 58)
    assert next(city for city in summary["cities"] if city["name"] == "Тверь")[
        "guide_available"
    ] is True

    monkeypatch.setattr(
        target, "list_city_manifests",
        lambda: (*original, SimpleNamespace(name="Тверь", slug="wrong-slug")),
    )
    with pytest.raises(RuntimeError, match="Reserved slug mismatch"):
        top_city_coverage()

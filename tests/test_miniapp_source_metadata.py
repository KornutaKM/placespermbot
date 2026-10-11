"""MVP-125: catalog provenance is publicly visible without leaking user data."""

import re

from fastapi.testclient import TestClient

from app.catalog import list_catalogs
from app.config import Settings
from app.miniapp_server import create_miniapp


def test_catalog_place_sources_exposed_for_all_registered_cities():
    app = TestClient(create_miniapp(Settings(
        bot_token="123456789:source-tests",
        database_path=":memory:",
        environment="development",
        city_slug="perm",
    )))
    with app:
        for catalog in list_catalogs():
            response = app.get(f"/api/catalogs/{catalog.slug}")
            assert response.status_code == 200
            places = response.json()["places"]
            assert len(places) == len(catalog.places)
            for place, original in zip(places, catalog.places, strict=True):
                assert place["source"] == {
                    "name": original.source.name,
                    "url": original.source.url,
                    "checked_at": original.source.checked_at.isoformat(),
                }
                assert place["source"]["url"].startswith("https://")
                assert re.fullmatch(
                    r"\d{4}-\d{2}-\d{2}", place["source"]["checked_at"]
                )
            assert "user_id" not in response.text


def test_cross_city_results_preserve_original_catalog_source():
    app = TestClient(create_miniapp(Settings(
        bot_token="123456789:source-tests",
        database_path=":memory:",
        environment="development",
        city_slug="perm",
    )))
    with app:
        result = app.get("/api/discover", params={"q": "музей", "limit": 30})
        assert result.status_code == 200
        places = result.json()["places"]
        assert places
        for item in places:
            source = next(
                place.source
                for catalog in list_catalogs() if catalog.slug == item["city_slug"]
                for place in catalog.places if place.slug == item["place_slug"]
            )
            assert item["source"]["name"] == source.name
            assert item["source"]["url"] == source.url
            assert item["source"]["checked_at"] == source.checked_at.isoformat()
        assert "initData" not in result.text

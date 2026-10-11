import asyncio
import hashlib
import hmac
import json
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from app.config import Settings
from app.database import migrate_database
from app.miniapp_server import create_miniapp
from app.storage import UserCityRepository


def authorize(token: str, user_id: int = 42) -> dict[str, str]:
    import time

    values = {
        "auth_date": str(int(time.time())),
        "user": json.dumps({"id": user_id, "first_name": "Guest"}),
    }
    check = "\n".join(f"{k}={v}" for k, v in sorted(values.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    hash_value = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return {"X-Telegram-Init-Data": urlencode({**values, "hash": hash_value})}


def client_for(tmp_path):
    db = str(tmp_path / "places.db")
    asyncio.run(migrate_database(db))
    token = "123456789:miniapp-server-test"
    settings = Settings(
        bot_token=token,
        database_path=db,
        environment="development",
        city_slug="saint-petersburg",
    )
    return TestClient(create_miniapp(settings)), db, token


def test_catalog_and_assets_are_public_but_private_info_is_not(tmp_path):
    client, _db, token = client_for(tmp_path)
    with client:
        cities = client.get("/api/cities")
        assert cities.status_code == 200
        assert len(cities.json()["cities"]) == 96
        assert client.get("/api/catalogs/not-a-city").status_code == 404

        catalog = client.get("/api/catalogs/perm")
        assert catalog.status_code == 200
        data = catalog.json()
        assert data["slug"] == "perm"
        assert len(data["places"]) > 0
        assert len(data["routes"]) > 0
        assert data["places"][0]["map_url"].startswith(
            "https://www.google.com/maps/search/"
        )
        assert "user_id" not in catalog.text
        assert token not in catalog.text

        assert client.get("/healthz").json()["status"] == "ok"
        page = client.get("/")
        assert page.status_code == 200
        assert "Город рядом" in page.text
        assert "/assets/app.js" in page.text
        assert "no-store" in page.headers["cache-control"]
        assert "telegram.org" in page.headers["content-security-policy"]
        assert page.headers["referrer-policy"] == (
            "strict-origin-when-cross-origin"
        )
        assert "https://tile.openstreetmap.org" in (
            page.headers["content-security-policy"]
        )
        assert "https://unpkg.com" in page.headers["content-security-policy"]
        assert "sha256-20nQCchB9co0qIjJZRGuk2" in page.text
        assert 'data-tab="map"' in page.text
        assert client.get("/assets/map.js").status_code == 200
        assert client.get("/assets/style.css").status_code == 200
        assert client.get("/assets/app.js").status_code == 200

        assert client.get("/api/me").status_code == 401
        assert client.post("/api/me/city", json={"city_slug": "perm"}).status_code == 401
        assert client.get("/api/me", headers={
            "X-Telegram-Init-Data": "user=42"
        }).status_code == 401


def test_signed_city_selection_matches_existing_bot_repository(tmp_path):
    client, db, token = client_for(tmp_path)
    user = authorize(token)
    other_user = authorize(token, 84)

    with client:
        assert client.get("/api/me", headers=user).json()["city_slug"] is None
        assert client.post(
            "/api/me/city", headers=user, json={"city_slug": "perm"}
        ).json() == {"city_slug": "perm", "city_name": "Пермь"}
        assert client.get("/api/me", headers=user).json() == {
            "city_slug": "perm"
        }
        assert client.get("/api/me", headers=other_user).json() == {
            "city_slug": None
        }
        assert client.post(
            "/api/me/city", headers=other_user, json={"city_slug": "unknown"}
        ).status_code == 404
        assert client.post(
            "/api/me/city", headers=user, json={"city_slug": ""}
        ).status_code == 422

    repo = UserCityRepository(db)
    assert asyncio.run(repo.get_city_slug(42)) == "perm"
    assert asyncio.run(repo.get_city_slug(84)) is None

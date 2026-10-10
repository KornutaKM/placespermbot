"""Mini App favorites share the classic Telegram bot's SQLite repository."""

import asyncio
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from app.catalog import get_catalog
from app.config import Settings
from app.database import migrate_database
from app.miniapp_server import create_miniapp
from app.storage import FavoritesRepository, UserCityRepository

TOKEN = "123456789:miniapp-favorite-test-token"


def signed_headers(user_id: int) -> dict[str, str]:
    fields = {
        "auth_date": str(int(time.time())),
        "user": json.dumps({"id": user_id}),
    }
    message = "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    signature = hmac.new(secret, message.encode(), hashlib.sha256).hexdigest()
    return {"X-Telegram-Init-Data": urlencode({**fields, "hash": signature})}


def fixture(tmp_path):
    database_path = str(tmp_path / "places.db")
    asyncio.run(migrate_database(database_path))
    settings = Settings(
        bot_token=TOKEN,
        database_path=database_path,
        environment="development",
    )
    return TestClient(create_miniapp(settings)), database_path


def test_favorites_require_signed_identity_and_active_city(tmp_path):
    client, database_path = fixture(tmp_path)
    path = "/api/me/favorites/perm"
    place_slug = get_catalog("perm").places[0].slug
    item = path + "/" + place_slug
    user = signed_headers(42)
    other = signed_headers(43)
    forged = {"X-Telegram-Init-Data": user["X-Telegram-Init-Data"] + "&id=43"}

    with client:
        for method, url in (
            (client.get, path),
            (client.put, item),
            (client.delete, item),
        ):
            assert method(url).status_code == 401
            assert method(url, headers=forged).status_code == 401
            assert method(url, headers=user).status_code == 409

        assert client.post(
            "/api/me/city", json={"city_slug": "perm"}, headers=user
        ).status_code == 200
        assert client.get(path, headers=other).status_code == 409
        assert client.put(item, headers=other).status_code == 409
        assert client.get("/api/me/favorites/nonexistent", headers=user).status_code == 404
        assert client.put(
            path + "/nonexistent", headers=user
        ).status_code == 404
        assert client.delete(
            path + "/nonexistent", headers=user
        ).status_code == 404
        assert client.get(path, headers=user).json()["place_slugs"] == []

    assert asyncio.run(
        FavoritesRepository(database_path).list_place_slugs(42, "perm")
    ) == ()


def test_favorites_round_trip_bot_sync_and_idempotency(tmp_path):
    client, database_path = fixture(tmp_path)
    catalog = get_catalog("perm")
    place_a, place_b = catalog.places[:2]
    user = signed_headers(42)
    other = signed_headers(43)
    path = "/api/me/favorites/perm"
    item = path + "/" + place_a.slug

    with client:
        assert client.post(
            "/api/me/city", json={"city_slug": "perm"}, headers=user
        ).status_code == 200
        assert client.post(
            "/api/me/city", json={"city_slug": "perm"}, headers=other
        ).status_code == 200

        for _ in range(2):
            added = client.put(item, headers=user)
            assert added.status_code == 200
            assert added.json()["is_favorite"] is True
        assert client.get(path, headers=user).json()["place_slugs"] == [place_a.slug]
        assert client.get(path, headers=other).json()["place_slugs"] == []

        repository = FavoritesRepository(database_path)
        assert asyncio.run(repository.contains(42, "perm", place_a.slug))
        asyncio.run(repository.add(42, "perm", place_b.slug))
        assert set(client.get(path, headers=user).json()["place_slugs"]) == {
            place_a.slug, place_b.slug
        }

        for _ in range(2):
            removed = client.delete(item, headers=user)
            assert removed.status_code == 200
            assert removed.json()["is_favorite"] is False
        assert client.get(path, headers=user).json()["place_slugs"] == [place_b.slug]
        assert not asyncio.run(repository.contains(42, "perm", place_a.slug))


def test_switching_city_preserves_other_city_favorites_and_hides_stale_rows(tmp_path):
    client, database_path = fixture(tmp_path)
    perm_place = get_catalog("perm").places[0].slug
    moscow_place = get_catalog("moscow").places[0].slug
    user = signed_headers(42)
    favorites = FavoritesRepository(database_path)
    city_store = UserCityRepository(database_path)

    asyncio.run(city_store.set_city_slug(42, "perm"))
    with client:
        assert client.put(
            "/api/me/favorites/perm/" + perm_place, headers=user
        ).status_code == 200
        asyncio.run(favorites.add(42, "perm", "removed-catalog-place"))
        assert client.get(
            "/api/me/favorites/perm", headers=user
        ).json()["place_slugs"] == [perm_place]

        assert client.post(
            "/api/me/city", json={"city_slug": "moscow"}, headers=user
        ).status_code == 200
        assert client.get("/api/me/favorites/perm", headers=user).status_code == 409
        assert client.delete(
            "/api/me/favorites/perm/" + perm_place, headers=user
        ).status_code == 409
        assert client.put(
            "/api/me/favorites/moscow/" + moscow_place, headers=user
        ).status_code == 200
        assert client.get(
            "/api/me/favorites/moscow", headers=user
        ).json()["place_slugs"] == [moscow_place]
        assert client.post(
            "/api/me/city", json={"city_slug": "perm"}, headers=user
        ).status_code == 200
        assert client.get(
            "/api/me/favorites/perm", headers=user
        ).json()["place_slugs"] == [perm_place]

    assert asyncio.run(favorites.contains(42, "perm", perm_place))
    assert asyncio.run(favorites.contains(42, "moscow", moscow_place))
    assert asyncio.run(favorites.contains(42, "perm", "removed-catalog-place"))

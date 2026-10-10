"""Mini App 'My Guide' uses existing, user-scoped Telegram bot persistence."""

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
from app.storage import (
    CompletedRoutesRepository,
    FavoritesRepository,
    SavedRoutesRepository,
    UserCityRepository,
    VisitedRepository,
)

TOKEN = "123456789:guide-api-test-token"


def signed(user_id: int) -> dict[str, str]:
    data = {
        "auth_date": str(int(time.time())),
        "user": json.dumps({"id": user_id}),
    }
    check = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    signature = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return {"X-Telegram-Init-Data": urlencode({**data, "hash": signature})}


def setup(tmp_path):
    db = str(tmp_path / "places.db")
    asyncio.run(migrate_database(db))
    app = create_miniapp(Settings(
        bot_token=TOKEN,
        database_path=db,
        environment="development",
        city_slug="saint-petersburg",
    ))
    return TestClient(app), db


def test_guide_endpoint_fails_closed_for_missing_user_and_other_city(tmp_path):
    client, db = setup(tmp_path)
    place = get_catalog("perm").places[0].slug
    guide = "/api/me/guide/perm"
    mark = "/api/me/visited/perm/" + place
    saved = "/api/me/saved-routes/perm/" + "a" * 16
    own = signed(42)
    outsider = signed(43)
    forged = {"X-Telegram-Init-Data": own["X-Telegram-Init-Data"] + "&id=43"}
    with client:
        for verb, path in (
            (client.get, guide),
            (client.put, mark),
            (client.delete, mark),
            (client.delete, saved),
            (client.put, saved + "/complete"),
        ):
            assert verb(path).status_code == 401
            assert verb(path, headers=forged).status_code == 401
            assert verb(path, headers=own).status_code == 409
        assert client.get("/api/me/guide/not-a-city", headers=own).status_code == 404
        assert client.post(
            "/api/me/city", json={"city_slug": "perm"}, headers=own
        ).status_code == 200
        assert client.get(guide, headers=outsider).status_code == 409
        assert client.put(mark, headers=outsider).status_code == 409
        assert client.put("/api/me/visited/perm/unknown", headers=own).status_code == 404
        assert client.delete("/api/me/visited/perm/unknown", headers=own).status_code == 404
        assert client.delete(saved, headers=own).status_code == 404
        assert client.put(saved + "/complete", headers=own).status_code == 404
        empty = client.get(guide, headers=own).json()
        assert empty["city_slug"] == "perm"
        assert empty["stats"] == {
            "favorites": 0, "visited": 0, "saved_routes": 0,
            "completed_routes": 0, "catalog_places": len(get_catalog("perm").places),
        }
        assert empty["saved_routes"] == empty["completed_routes"] == []
    assert asyncio.run(VisitedRepository(db).list_place_slugs(42, "perm")) == ()


def test_guide_visited_and_saved_route_lifecycle_matches_telegram(tmp_path):
    client, db = setup(tmp_path)
    city = get_catalog("perm")
    p1, p2 = city.places[:2]
    favorites = FavoritesRepository(db)
    visited = VisitedRepository(db)
    saved = SavedRoutesRepository(db)
    completed = CompletedRoutesRepository(db)
    user = signed(42)
    other = signed(43)
    asyncio.run(UserCityRepository(db).set_city_slug(42, "perm"))
    asyncio.run(UserCityRepository(db).set_city_slug(43, "perm"))
    route = asyncio.run(saved.save(
        42, "perm", "classic", 240, (p1.slug, p2.slug)
    ))
    asyncio.run(favorites.add(42, "perm", p1.slug))
    asyncio.run(favorites.add(42, "perm", "obsolete-favorite"))
    asyncio.run(visited.add(42, "perm", "obsolete-visited"))
    guide_url = "/api/me/guide/perm"
    route_url = "/api/me/saved-routes/perm/" + route.route_id

    with client:
        first = client.get(guide_url, headers=user).json()
        assert first["favorite_slugs"] == [p1.slug]
        assert first["visited_slugs"] == []
        assert first["stats"]["saved_routes"] == 1
        assert first["saved_routes"][0]["route_id"] == route.route_id
        assert first["saved_routes"][0]["place_count"] == 2
        assert first["saved_routes"][0]["unavailable_count"] == 0
        assert first["saved_routes"][0]["completed"] is False
        assert first["saved_routes"][0]["map_links"]
        assert client.get(guide_url, headers=other).json()["saved_routes"] == []
        assert client.put(route_url + "/complete", headers=other).status_code == 404
        assert client.delete(route_url, headers=other).status_code == 404

        item = "/api/me/visited/perm/" + p1.slug
        for _ in range(2):
            response = client.put(item, headers=user)
            assert response.status_code == 200
            assert response.json()["is_visited"] is True
        assert client.get(guide_url, headers=user).json()["visited_slugs"] == [p1.slug]
        for _ in range(2):
            response = client.delete(item, headers=user)
            assert response.status_code == 200
            assert response.json()["is_visited"] is False
        assert client.get(guide_url, headers=user).json()["stats"]["visited"] == 0

        finish = client.put(route_url + "/complete", headers=user)
        assert finish.status_code == 200
        assert finish.json()["added"] == 2
        assert finish.json()["already_completed"] is False
        repeat = client.put(route_url + "/complete", headers=user)
        assert repeat.status_code == 200
        assert repeat.json()["already_completed"] is True
        after_finish = client.get(guide_url, headers=user).json()
        assert set(after_finish["visited_slugs"]) == {p1.slug, p2.slug}
        assert after_finish["stats"]["completed_routes"] == 1
        assert after_finish["saved_routes"][0]["completed"] is True
        assert after_finish["completed_routes"][0]["route_id"] == route.route_id

        deleted = client.delete(route_url, headers=user)
        assert deleted.status_code == 200
        assert deleted.json()["deleted"] is True
        assert client.delete(route_url, headers=user).status_code == 404
        final = client.get(guide_url, headers=user).json()
        assert final["saved_routes"] == []
        assert final["stats"]["saved_routes"] == 0
        assert final["stats"]["completed_routes"] == 1
        assert final["completed_routes"][0]["route_id"] == route.route_id
        assert client.put(route_url + "/complete", headers=user).status_code == 404

    assert asyncio.run(completed.contains(42, "perm", route.route_id))
    assert asyncio.run(saved.get(42, "perm", route.route_id)) is None
    assert asyncio.run(visited.contains(42, "perm", p1.slug))
    assert asyncio.run(favorites.contains(42, "perm", "obsolete-favorite"))


def test_guide_city_switch_keeps_each_history_separate(tmp_path):
    client, db = setup(tmp_path)
    user = signed(42)
    city_store = UserCityRepository(db)
    repository = VisitedRepository(db)
    perm = get_catalog("perm").places[0].slug
    moscow = get_catalog("moscow").places[0].slug
    asyncio.run(city_store.set_city_slug(42, "perm"))
    with client:
        assert client.put(
            "/api/me/visited/perm/" + perm, headers=user
        ).status_code == 200
        assert client.post(
            "/api/me/city", headers=user, json={"city_slug": "moscow"}
        ).status_code == 200
        assert client.get("/api/me/guide/perm", headers=user).status_code == 409
        assert client.delete(
            "/api/me/visited/perm/" + perm, headers=user
        ).status_code == 409
        assert client.put(
            "/api/me/visited/moscow/" + moscow, headers=user
        ).status_code == 200
        assert client.get(
            "/api/me/guide/moscow", headers=user
        ).json()["visited_slugs"] == [moscow]
        assert client.post(
            "/api/me/city", headers=user, json={"city_slug": "perm"}
        ).status_code == 200
        assert client.get(
            "/api/me/guide/perm", headers=user
        ).json()["visited_slugs"] == [perm]
    assert asyncio.run(repository.contains(42, "moscow", moscow))
    assert asyncio.run(repository.contains(42, "perm", perm))

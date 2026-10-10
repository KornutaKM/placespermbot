"""Route builder previews are safe; saved routes are always reconstructed server-side."""

import asyncio
import hashlib
import hmac
import json
import time
from itertools import pairwise
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

from app.catalog import distance_km, list_catalogs
from app.config import Settings
from app.database import migrate_database
from app.miniapp_route_builder import RouteBuildRequest, build_miniapp_route, route_preview
from app.miniapp_server import create_miniapp
from app.planner import INTEREST_LABELS, MAX_GENERATED_WALK_LEG_KM
from app.saved_routes import route_id_for
from app.storage import SavedRoutesRepository, UserCityRepository, VisitedRepository

TOKEN = "123456789:builder-tests"


def signed_headers(user_id: int) -> dict[str, str]:
    data = {
        "auth_date": str(int(time.time())),
        "user": json.dumps({"id": user_id}),
    }
    check = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    signature = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return {"X-Telegram-Init-Data": urlencode({**data, "hash": signature})}


def fixture(tmp_path):
    db = str(tmp_path / "places.db")
    asyncio.run(migrate_database(db))
    app = create_miniapp(Settings(
        bot_token=TOKEN, database_path=db, environment="development"
    ))
    return TestClient(app), db


@pytest.mark.parametrize("interest", tuple(INTEREST_LABELS))
@pytest.mark.parametrize("budget", (120, 240, 360))
def test_route_builder_respects_geometry_budget_and_accounting(interest, budget):
    for city in list_catalogs():
        body = RouteBuildRequest(budget_minutes=budget, interest=interest)
        route = build_miniapp_route(city, body)
        if route is None:
            continue
        data = route_preview(city, route)
        assert data["route_id"] == route_id_for(
            city.slug, interest, budget, tuple(p.slug for p in route.places)
        )
        assert data["estimated_minutes"] <= budget
        assert data["visit_minutes"] + data["walking_minutes"] == data["estimated_minutes"]
        assert data["estimated_minutes"] + data["spare_minutes"] == budget
        assert data["distance_km"] == route.distance_km
        assert len(data["places"]) == len(route.places)
        assert len({p.slug for p in route.places}) == len(route.places)
        assert all(
            distance_km(left, right) <= MAX_GENERATED_WALK_LEG_KM
            for left, right in pairwise(route.places)
        )
        assert all(link["url"].startswith("https://www.google.com/maps/")
                   for link in data["map_links"])


def test_public_preview_auth_gates_and_invalid_payloads(tmp_path):
    client, db = fixture(tmp_path)
    base = "/api/routes/perm/preview"
    payload = {"interest": "classic", "budget_minutes": 240}
    with client:
        preview = client.post(base, json=payload)
        assert preview.status_code == 200
        data = preview.json()
        assert data["city_slug"] == "perm"
        assert data["places"]
        assert data["estimated_minutes"] <= 240
        assert client.post(base, json={**payload, "exclude_visited": True}).status_code == 401
        assert client.post(base, json={**payload, "exclude_visited": True},
                           headers={"X-Telegram-Init-Data": "invalid"}).status_code == 401
        assert client.post("/api/routes/nonexistent/preview", json=payload).status_code == 404
        for wrong in (
            {**payload, "interest": "personal"},
            {**payload, "budget_minutes": 180},
            {**payload, "budget_minutes": -1},
            {**payload, "place_slugs": ["forged"]},
            {**payload, "exclude_visited": "invalid"},
        ):
            assert client.post(base, json=wrong).status_code == 422
        assert client.post(
            "/api/me/routes/perm/save", json={**payload, "expected_route_id": data["route_id"]}
        ).status_code == 401
    assert asyncio.run(SavedRoutesRepository(db).list_routes(42, "perm")) == ()


def test_authenticated_preview_excludes_only_own_visited_and_saves_idempotently(tmp_path):
    client, db = fixture(tmp_path)
    own = signed_headers(42)
    other = signed_headers(43)
    outsider = signed_headers(44)
    request = {"interest": "classic", "budget_minutes": 240, "exclude_visited": True}
    public = {"interest": "classic", "budget_minutes": 240}
    base = "/api/routes/perm/preview"
    repo = SavedRoutesRepository(db)
    visit_repo = VisitedRepository(db)
    city_repo = UserCityRepository(db)
    with client:
        regular = client.post(base, json=public).json()
        first = regular["places"][0]["slug"]
        asyncio.run(visit_repo.add(42, "perm", first))
        asyncio.run(visit_repo.add(43, "perm", "removed-catalog-object"))
        assert client.post(base, json=request, headers=own).status_code == 409
        assert client.post("/api/me/city", headers=own,
                           json={"city_slug": "perm"}).status_code == 200
        assert client.post("/api/me/city", headers=other,
                           json={"city_slug": "perm"}).status_code == 200

        excluded = client.post(base, json=request, headers=own)
        assert excluded.status_code == 200
        route = excluded.json()
        assert first not in [place["slug"] for place in route["places"]]
        second = client.post(base, json=request, headers=other).json()
        assert first in [place["slug"] for place in second["places"]]
        assert route["route_id"] != regular["route_id"]

        save_url = "/api/me/routes/perm/save"
        save_body = {**request, "expected_route_id": route["route_id"]}
        assert client.post(save_url, json=save_body).status_code == 401
        assert client.post(save_url, headers=outsider, json=save_body).status_code == 409
        assert client.post(save_url, headers=own, json={
            **save_body, "expected_route_id": "0" * 16
        }).status_code == 409
        assert client.post(save_url, headers=own, json={
            **save_body, "expected_route_id": "not-a-route-id"
        }).status_code == 422
        assert asyncio.run(repo.list_routes(42, "perm")) == ()

        for _ in range(2):
            result = client.post(save_url, headers=own, json=save_body)
            assert result.status_code == 200
            assert result.json()["route_id"] == route["route_id"]
            assert result.json()["saved"] is True
        saved = asyncio.run(repo.list_routes(42, "perm"))
        assert len(saved) == 1
        assert saved[0].place_slugs == tuple(p["slug"] for p in route["places"])
        assert asyncio.run(repo.list_routes(43, "perm")) == ()
        guide = client.get("/api/me/guide/perm", headers=own).json()
        assert guide["saved_routes"][0]["route_id"] == route["route_id"]

        # Another visit after preview invalidates the previously shown snapshot.
        next_slug = route["places"][0]["slug"]
        asyncio.run(visit_repo.add(42, "perm", next_slug))
        assert client.post(save_url, headers=own, json=save_body).status_code == 409
        assert len(asyncio.run(repo.list_routes(42, "perm"))) == 1

        # Other city cannot be written while Perm is selected.
        assert client.post("/api/me/routes/moscow/save", headers=own,
                           json=save_body).status_code == 409
        assert client.post("/api/routes/moscow/preview", headers=own,
                           json=request).status_code == 409
    assert asyncio.run(city_repo.get_city_slug(42)) == "perm"


def test_public_preview_can_save_without_visited_filter_when_signed(tmp_path):
    client, db = fixture(tmp_path)
    own = signed_headers(42)
    body = {"interest": "free", "budget_minutes": 120, "exclude_visited": False}
    with client:
        preview = client.post("/api/routes/perm/preview", json=body)
        assert preview.status_code == 200
        route_id = preview.json()["route_id"]
        assert client.post(
            "/api/me/routes/perm/save", headers=own,
            json={**body, "expected_route_id": route_id}
        ).status_code == 409
        assert client.post("/api/me/city", headers=own,
                           json={"city_slug": "perm"}).status_code == 200
        saved = client.post("/api/me/routes/perm/save", headers=own,
                            json={**body, "expected_route_id": route_id})
        assert saved.status_code == 200
        assert saved.json()["place_count"] == len(preview.json()["places"])
    assert len(asyncio.run(SavedRoutesRepository(db).list_routes(42, "perm"))) == 1

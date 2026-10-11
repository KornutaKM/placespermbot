"""Alternative-stop discovery and saving cannot bypass the canonical planner."""

import asyncio
import hashlib
import hmac
import json
import time
from itertools import pairwise
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

from app.catalog import distance_km, get_catalog, list_catalogs
from app.config import Settings
from app.database import migrate_database
from app.miniapp_route_builder import (
    RouteAlternativesRequest,
    RouteBuildRequest,
    RouteReplacementRequest,
    alternative_routes,
    build_miniapp_route,
    replaced_miniapp_route,
)
from app.miniapp_server import create_miniapp
from app.storage import SavedRoutesRepository, VisitedRepository

TOKEN = "123456789:alternative-tests"


def signed(user_id: int) -> dict[str, str]:
    data = {"auth_date": str(int(time.time())),
            "user": json.dumps({"id": user_id})}
    check = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    mac = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return {"X-Telegram-Init-Data": urlencode({**data, "hash": mac})}


def client_for(tmp_path):
    db = str(tmp_path / "places.db")
    asyncio.run(migrate_database(db))
    return TestClient(create_miniapp(Settings(
        bot_token=TOKEN, database_path=db, environment="development",
    ))), db


def request_for(city_slug="suzdal", *, visited=False):
    catalog = get_catalog(city_slug)
    original = build_miniapp_route(catalog, RouteBuildRequest(
        budget_minutes=240, interest="classic", exclude_visited=visited
    ))
    assert original is not None
    from app.saved_routes import route_id_for
    slugs = [p.slug for p in original.places]
    data = {
        "budget_minutes": 240, "interest": "classic",
        "exclude_visited": visited,
        "base_route_id": route_id_for(
            city_slug, "classic", 240, tuple(slugs)
        ),
        "place_slugs": slugs,
        "stop_index": 0,
    }
    return data


def test_suggested_replacements_are_safe_and_deterministic_across_all_cities():
    explored = 0
    found = 0
    for city in list_catalogs():
        for interest in ("classic", "museums", "walks", "free"):
            original = build_miniapp_route(city, RouteBuildRequest(
                budget_minutes=360, interest=interest
            ))
            if original is None:
                continue
            explored += 1
            from app.saved_routes import route_id_for
            request = RouteAlternativesRequest(
                budget_minutes=360,
                interest=interest,
                base_route_id=route_id_for(
                    city.slug, interest, 360,
                    tuple(place.slug for place in original.places),
                ),
                place_slugs=[p.slug for p in original.places],
                stop_index=0,
            )
            proposals = alternative_routes(city, request)
            assert len(proposals) <= 8
            assert proposals == alternative_routes(city, request)
            for candidate, route in proposals:
                found += 1
                assert candidate.slug not in request.place_slugs
                assert route.estimated_minutes <= 360
                assert len(route.places) == len(original.places)
                assert route.places[0].slug == candidate.slug
                assert all(
                    distance_km(first, second) <= 5.0
                    for first, second in pairwise(route.places)
                )
    assert explored >= 45
    assert found > 10


def test_preview_and_save_replacement_are_scoped_and_idempotent(tmp_path):
    client, db = client_for(tmp_path)
    original = request_for()
    root = "/api/routes/suzdal"
    own, other = signed(42), signed(43)
    with client:
        options = client.post(root + "/alternatives", json=original)
        assert options.status_code == 200
        choices = options.json()["alternatives"]
        assert choices, "Suzdal classic route should offer another location"
        candidate = choices[0]["slug"]
        assert candidate not in original["place_slugs"]
        assert choices[0]["estimated_minutes"] <= 240
        replacement = {**original, "candidate_slug": candidate}
        response = client.post(root + "/replace", json=replacement)
        assert response.status_code == 200
        edited = response.json()
        assert edited["route_id"] != original["base_route_id"]
        assert edited["places"][0]["slug"] == candidate
        assert [p["slug"] for p in edited["places"][1:]] == (
            original["place_slugs"][1:]
        )
        assert edited["estimated_minutes"] <= 240
        assert edited["visit_minutes"] + edited["walking_minutes"] == (
            edited["estimated_minutes"]
        )
        assert edited["spare_minutes"] >= 0

        save_url = "/api/me/routes/suzdal/save-replaced"
        body = {**replacement, "expected_route_id": edited["route_id"]}
        assert client.post(save_url, json=body).status_code == 401
        assert client.post(save_url, headers=own, json=body).status_code == 409
        assert client.post("/api/me/city", headers=own, json={
            "city_slug": "suzdal"
        }).status_code == 200
        assert client.post("/api/me/city", headers=other, json={
            "city_slug": "suzdal"
        }).status_code == 200
        assert client.post(save_url, headers=own, json={
            **body, "expected_route_id": "0" * 16
        }).status_code == 409
        assert client.post(save_url, headers=own, json={
            **body, "candidate_slug": "forged-place"
        }).status_code == 409
        assert client.post(save_url, headers=own, json={
            **body, "base_route_id": "0" * 16
        }).status_code == 409
        assert client.post(save_url, headers=own, json={
            **body, "place_slugs": ["forged-stop"]
        }).status_code == 409
        assert client.post(save_url, headers=own, json={
            **body, "stop_index": 99
        }).status_code == 422
        assert asyncio.run(SavedRoutesRepository(db).list_routes(42, "suzdal")) == ()

        for _ in range(2):
            result = client.post(save_url, headers=own, json=body)
            assert result.status_code == 200
            assert result.json()["saved"] is True
            assert result.json()["route_id"] == edited["route_id"]
        routes = asyncio.run(SavedRoutesRepository(db).list_routes(42, "suzdal"))
        assert len(routes) == 1
        assert routes[0].place_slugs == tuple(
            p["slug"] for p in edited["places"]
        )
        assert not asyncio.run(SavedRoutesRepository(db).list_routes(43, "suzdal"))
        assert client.get(
            "/api/me/guide/suzdal", headers=own
        ).json()["saved_routes"][0]["route_id"] == edited["route_id"]
        assert client.post("/api/me/routes/perm/save-replaced", headers=own,
                           json=body).status_code == 409


def test_replacement_auth_and_expired_visited_filters(tmp_path):
    client, db = client_for(tmp_path)
    request = request_for(visited=True)
    own = signed(42)
    with client:
        assert client.post(
            "/api/routes/suzdal/alternatives", json=request
        ).status_code == 401
        assert client.post(
            "/api/routes/suzdal/replace",
            json={**request, "candidate_slug": "forged"}
        ).status_code == 401
        assert client.post("/api/me/city", headers=own, json={
            "city_slug": "suzdal"
        }).status_code == 200
        options = client.post(
            "/api/routes/suzdal/alternatives", headers=own, json=request
        )
        assert options.status_code == 200
        choices = options.json()["alternatives"]
        assert choices
        candidate = choices[0]["slug"]
        preview = client.post(
            "/api/routes/suzdal/replace", headers=own,
            json={**request, "candidate_slug": candidate}
        )
        assert preview.status_code == 200
        asyncio.run(
            VisitedRepository(db).add(42, "suzdal", request["place_slugs"][0])
        )
        stale_body = {
            **request, "candidate_slug": candidate,
            "expected_route_id": preview.json()["route_id"],
        }
        assert client.post(
            "/api/routes/suzdal/alternatives", headers=own,
            json=request
        ).status_code == 409
        assert client.post(
            "/api/me/routes/suzdal/save-replaced",
            headers=own, json=stale_body
        ).status_code == 409
        assert asyncio.run(SavedRoutesRepository(db).list_routes(42, "suzdal")) == ()


def test_replacement_models_reject_client_additions_and_unsafe_stop_index():
    catalog = get_catalog("suzdal")
    good = request_for()
    with pytest.raises(ValueError, match="Duplicate"):
        alternative_routes(
            catalog, RouteAlternativesRequest(
                **{**good, "place_slugs": [good["place_slugs"][0]] * 2}
            )
        )
    bad = RouteReplacementRequest(
        **{**good, "candidate_slug": "unknown-place"}
    )
    with pytest.raises(ValueError, match="not among safe"):
        replaced_miniapp_route(catalog, bad)

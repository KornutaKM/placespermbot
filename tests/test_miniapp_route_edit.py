"""Mini App stop editing always replays canonical planning before saving."""

import asyncio
import hashlib
import hmac
import json
import time
from datetime import date
from itertools import pairwise
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

from app.catalog import distance_km, get_catalog, list_catalogs
from app.config import Settings
from app.database import migrate_database
from app.domain import GeneratedRoute, Place, PlaceSource
from app.miniapp_route_builder import (
    RouteEditRequest,
    build_miniapp_route,
    edited_miniapp_route,
    route_preview,
)
from app.miniapp_server import create_miniapp
from app.planner import INTEREST_LABELS, MAX_GENERATED_WALK_LEG_KM
from app.saved_routes import route_id_for
from app.storage import SavedRoutesRepository, VisitedRepository

TOKEN = "123456789:route-editor-tests"


def signed(user_id: int) -> dict[str, str]:
    data = {
        "auth_date": str(int(time.time())),
        "user": json.dumps({"id": user_id}),
    }
    check = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    signature = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return {"X-Telegram-Init-Data": urlencode({**data, "hash": signature})}


def client_with_db(tmp_path):
    db = str(tmp_path / "places.db")
    asyncio.run(migrate_database(db))
    app = create_miniapp(Settings(
        bot_token=TOKEN, database_path=db, environment="development"
    ))
    return TestClient(app), db


def payload_for(catalog, original, slugs):
    return RouteEditRequest(
        budget_minutes=original.budget_minutes,
        interest=original.interest,
        base_route_id=route_id_for(
            catalog.slug, original.interest, original.budget_minutes,
            tuple(place.slug for place in original.places)
        ),
        place_slugs=list(slugs),
    )


@pytest.mark.parametrize("interest", tuple(INTEREST_LABELS))
@pytest.mark.parametrize("minutes", (120, 240, 360))
def test_every_city_stop_removals_respect_budget_and_geometry(interest, minutes):
    for city in list_catalogs():
        from app.miniapp_route_builder import RouteBuildRequest

        original = build_miniapp_route(
            city, RouteBuildRequest(budget_minutes=minutes, interest=interest)
        )
        if original is None or len(original.places) < 2:
            continue
        for chosen in (original.places[1:], original.places[:-1]):
            body = payload_for(city, original, (place.slug for place in chosen))
            edited = edited_miniapp_route(city, body)
            data = route_preview(city, edited)
            assert tuple(place.slug for place in edited.places) == tuple(
                place.slug for place in chosen
            )
            assert edited.estimated_minutes <= minutes
            assert data["visit_minutes"] + data["walking_minutes"] == (
                data["estimated_minutes"]
            )
            assert data["estimated_minutes"] + data["spare_minutes"] == minutes
            assert all(
                distance_km(left, right) <= MAX_GENERATED_WALK_LEG_KM
                for left, right in pairwise(edited.places)
            )


def test_editor_fails_closed_on_forged_slugs_duplicate_or_stale_baseline():
    city = get_catalog("perm")
    from app.miniapp_route_builder import RouteBuildRequest

    route = build_miniapp_route(
        city, RouteBuildRequest(budget_minutes=240, interest="classic")
    )
    assert route is not None
    slugs = [place.slug for place in route.places]
    base = payload_for(city, route, slugs)
    assert edited_miniapp_route(city, base).places == route.places
    with pytest.raises(ValueError, match="Duplicate"):
        edited_miniapp_route(
            city, base.model_copy(update={"place_slugs": [slugs[0]] * 2})
        )
    with pytest.raises(ValueError, match="original generated"):
        edited_miniapp_route(
            city, base.model_copy(update={"place_slugs": [slugs[0], "forged"]})
        )
    with pytest.raises(ValueError, match="original route changed"):
        edited_miniapp_route(
            city, base.model_copy(update={"base_route_id": "0" * 16})
        )


def test_editor_rejects_unsafe_new_bridge_and_edited_time_budget():
    from app.catalog import distance_km

    source = PlaceSource("Test", "https://example.org/", date(2026, 10, 1))
    stops = tuple(
        Place(
            slug=f"stop-{i}", title=f"Stop {i}", category="sights",
            summary="Mock", emoji="🏛", district="centre", visit_minutes=70,
            is_free=True, latitude=55.0 + i * 0.035,
            longitude=37.0, source=source,
        ) for i in range(3)
    )
    assert distance_km(stops[0], stops[1]) < MAX_GENERATED_WALK_LEG_KM
    assert distance_km(stops[0], stops[2]) > MAX_GENERATED_WALK_LEG_KM
    baseline = GeneratedRoute(
        interest="classic", budget_minutes=360,
        estimated_minutes=315, distance_km=7.8, places=stops
    )
    city = SimpleNamespace(slug="perm")
    with patch("app.miniapp_route_builder.build_miniapp_route", return_value=baseline):
        bridge = payload_for(city, baseline, [stops[0].slug, stops[2].slug])
        with pytest.raises(ValueError, match="5 km"):
            edited_miniapp_route(city, bridge)
        over = payload_for(city, baseline, [stops[0].slug, stops[1].slug])
        over = over.model_copy(update={"budget_minutes": 120})
        # The mocked canonical planner proves the time-budget gate independently.
        over = over.model_copy(update={"base_route_id": route_id_for(
            "perm", "classic", 120, tuple(p.slug for p in stops)
        )})
        with pytest.raises(ValueError, match="time budget"):
            edited_miniapp_route(city, over)


def test_edit_preview_and_save_are_separate_and_user_scoped(tmp_path):
    client, db = client_with_db(tmp_path)
    user, other = signed(42), signed(43)
    root = "/api/routes/perm"
    originals = {"budget_minutes": 240, "interest": "classic",
                 "exclude_visited": False}
    with client:
        base = client.post(root + "/preview", json=originals).json()
        slugs = [place["slug"] for place in base["places"]]
        assert len(slugs) > 1
        request = {
            **originals, "base_route_id": base["route_id"],
            "place_slugs": slugs[:-1],
        }
        edit = client.post(root + "/edit", json=request)
        assert edit.status_code == 200
        updated = edit.json()
        assert [p["slug"] for p in updated["places"]] == slugs[:-1]
        assert updated["route_id"] != base["route_id"]
        assert updated["estimated_minutes"] <= 240
        assert updated["map_links"]
        assert client.post(root + "/edit", json={
            **request, "place_slugs": ["forged-stop"]
        }).status_code == 422
        assert client.post(root + "/edit", json={
            **request, "place_slugs": [slugs[0], slugs[0]]
        }).status_code == 422
        assert client.post(root + "/edit", json={
            **request, "base_route_id": "0" * 16
        }).status_code == 409
        assert client.post(root + "/edit", json={
            **request, "place_slugs": []
        }).status_code == 422

        save = "/api/me/routes/perm/save-edited"
        save_body = {**request, "expected_route_id": updated["route_id"]}
        assert client.post(save, json=save_body).status_code == 401
        assert client.post(save, headers=user, json=save_body).status_code == 409
        assert client.post("/api/me/city", json={
            "city_slug": "perm"
        }, headers=user).status_code == 200
        assert client.post(save, headers=other, json=save_body).status_code == 409
        for wrong in (
            {**save_body, "expected_route_id": base["route_id"]},
            {**save_body, "base_route_id": "0" * 16},
            {**save_body, "place_slugs": [slugs[0], "forged"]},
        ):
            assert client.post(save, headers=user, json=wrong).status_code == 409
        assert asyncio.run(SavedRoutesRepository(db).list_routes(42, "perm")) == ()

        for _ in range(2):
            response = client.post(save, headers=user, json=save_body)
            assert response.status_code == 200
            assert response.json()["route_id"] == updated["route_id"]
        saved = asyncio.run(SavedRoutesRepository(db).list_routes(42, "perm"))
        assert len(saved) == 1
        assert saved[0].place_slugs == tuple(slugs[:-1])
        assert asyncio.run(SavedRoutesRepository(db).list_routes(43, "perm")) == ()
        assert client.get(
            "/api/me/guide/perm", headers=user
        ).json()["saved_routes"][0]["route_id"] == updated["route_id"]
        assert client.post("/api/me/routes/moscow/save-edited",
                           json=save_body, headers=user).status_code == 409


def test_excluded_visited_changes_invalidate_edited_route_before_save(tmp_path):
    client, db = client_with_db(tmp_path)
    user = signed(42)
    query = {"budget_minutes": 240, "interest": "classic",
             "exclude_visited": True}
    with client:
        assert client.post("/api/routes/perm/preview", json=query).status_code == 401
        assert client.post("/api/me/city", headers=user,
                           json={"city_slug": "perm"}).status_code == 200
        baseline = client.post(
            "/api/routes/perm/preview", headers=user, json=query
        ).json()
        slugs = [p["slug"] for p in baseline["places"]]
        assert len(slugs) > 1
        edited_payload = {
            **query, "base_route_id": baseline["route_id"],
            "place_slugs": slugs[:-1],
        }
        edited = client.post(
            "/api/routes/perm/edit", headers=user, json=edited_payload
        )
        assert edited.status_code == 200
        result = edited.json()
        asyncio.run(VisitedRepository(db).add(42, "perm", slugs[0]))
        assert client.post("/api/routes/perm/edit", headers=user,
                           json=edited_payload).status_code == 409
        response = client.post(
            "/api/me/routes/perm/save-edited", headers=user,
            json={**edited_payload, "expected_route_id": result["route_id"]}
        )
        assert response.status_code == 409
        assert asyncio.run(SavedRoutesRepository(db).list_routes(42, "perm")) == ()

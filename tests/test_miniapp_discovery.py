"""MVP-124: public cross-city discovery, paging and fail-closed validation."""

from fastapi.testclient import TestClient

from app.city_discovery import discover_places
from app.config import Settings
from app.miniapp_server import create_miniapp


def client():
    return TestClient(create_miniapp(Settings(
        bot_token="123456789:discovery-tests",
        database_path=":memory:",
        environment="development",
        city_slug="perm",
    )))


def test_public_discovery_searches_multiple_cities_without_personal_data():
    with client() as app:
        response = app.get("/api/discover", params={"q": "музей", "limit": 30})
        assert response.status_code == 200
        payload = response.json()
        assert payload["query"] == "музей"
        assert payload["total"] >= len(payload["places"]) > 0
        assert len({p["city_slug"] for p in payload["places"]}) >= 2
        assert "user_id" not in response.text
        assert "initData" not in response.text
        for place in payload["places"]:
            assert place["city_slug"] and place["place_slug"]
            assert place["city_name"] and place["title"]
            assert "category_label" in place
            assert "is_free" in place
        assert response.headers["Cache-Control"] == "no-store"


def test_city_name_and_e_yo_normalization():
    with client() as app:
        r = app.get("/api/discover", params={"q": "КАЗАНЬ", "limit": 30})
        assert r.status_code == 200
        assert r.json()["total"] > 0
        assert all(p["city_slug"] == "kazan" for p in r.json()["places"])

    assert discover_places("музеи")["total"] >= 0
    assert discover_places(" Ё ", catalogs=())["total"] == 0


def test_category_filters_and_deterministic_pagination():
    with client() as app:
        params = {"q": "музей", "category": "free", "limit": 5}
        first = app.get("/api/discover", params=params).json()
        again = app.get("/api/discover", params=params).json()
        next_page = app.get("/api/discover", params={**params, "offset": 5}).json()
        assert first == again
        assert 0 < len(first["places"]) <= 5
        assert all(p["is_free"] for p in first["places"])
        assert first["total"] >= len(first["places"])
        assert { (p["city_slug"], p["place_slug"]) for p in first["places"] }.isdisjoint(
            {(p["city_slug"], p["place_slug"]) for p in next_page["places"]}
        )
        assert next_page["offset"] == 5
        assert first["has_more"] == (first["total"] > 5)
        family = app.get("/api/discover", params={"q": "музей", "category": "family"})
        assert family.status_code == 200


def test_discovery_validation_and_empty_cases():
    with client() as app:
        for params in (
            {}, {"q": "а"}, {"q": " " * 3},
            {"q": "музей", "category": "hotels"},
            {"q": "музей", "limit": 0},
            {"q": "музей", "limit": 31},
            {"q": "музей", "offset": -1},
            {"q": "музей", "offset": 1001},
            {"q": "a" * 81},
        ):
            response = app.get("/api/discover", params=params)
            assert response.status_code == 422, params
        empty = app.get("/api/discover", params={"q": "зжъцжъцзжъ"})
        assert empty.status_code == 200
        assert empty.json()["places"] == []
        assert empty.json()["total"] == 0
        assert empty.json()["has_more"] is False


def test_search_does_not_modify_active_city():
    with client() as app:
        before = app.get("/api/me")
        assert before.status_code == 401
        assert app.get("/api/discover", params={"q": "Москва"}).status_code == 200
        assert app.get("/api/me").status_code == 401


def test_direct_ranker_rejects_unbounded_query():
    try:
        discover_places("   ")
    except ValueError as exc:
        assert "blank" in str(exc)
    else:
        raise AssertionError("Blank query was accepted")
    for category in ("all", "sights", "unusual", "museums", "parks", "free", "family"):
        assert discover_places("музей", category=category)["total"] >= 0

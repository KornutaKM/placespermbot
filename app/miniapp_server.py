"""Read-only city catalog API with signed Telegram identity for preferences."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.catalog import get_catalog, has_catalog
from app.catalog_service import CatalogService
from app.config import Settings, get_settings
from app.maps import google_maps_place_url, google_maps_route_links
from app.miniapp_auth import InvalidTelegramInitData, validate_init_data
from app.miniapp_profile import my_guide_snapshot
from app.miniapp_route_builder import (
    RouteBuildRequest,
    SaveBuiltRouteRequest,
    build_miniapp_route,
    route_preview,
)
from app.route_completion import complete_saved_route
from app.storage import (
    CompletedRoutesRepository,
    FavoritesRepository,
    SavedRoutesRepository,
    UserCityRepository,
    VisitedRepository,
)

STATIC_DIR = Path(__file__).resolve().parent / "miniapp_static"


class CitySelection(BaseModel):
    city_slug: str = Field(min_length=1, max_length=80)


def create_miniapp(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else get_settings()
    cities = CatalogService(
        default_city_slug=config.city_slug,
        user_city_repo=UserCityRepository(config.database_path),
    )
    favorites = FavoritesRepository(config.database_path)
    visited = VisitedRepository(config.database_path)
    saved_routes = SavedRoutesRepository(config.database_path)
    completed_routes = CompletedRoutesRepository(config.database_path)
    app = FastAPI(
        title="Places Mini App",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; "
            "script-src 'self' https://telegram.org https://unpkg.com; "
            "style-src 'self' https://unpkg.com; "
            "img-src 'self' data: https://tile.openstreetmap.org https://unpkg.com; "
            "connect-src 'self'; "
            "font-src 'self'; "
            "base-uri 'none'; form-action 'none'"
        )
        return response

    def authenticated_user(raw_init_data: str | None) -> int:
        try:
            token = config.require_bot_token()
            return validate_init_data(raw_init_data or "", token)
        except (InvalidTelegramInitData, RuntimeError) as exc:
            raise HTTPException(status_code=401, detail="Telegram authorization required") from exc

    @app.get("/")
    async def index():
        return FileResponse(STATIC_DIR / "index.html", media_type="text/html")

    @app.get("/healthz")
    async def healthz():
        return {"status": "ok"}

    @app.get("/api/cities")
    async def list_cities():
        return {
            "cities": [
                {
                    "slug": city.slug,
                    "name": city.name,
                    "places_count": len(city.places),
                    "routes_count": len(city.routes),
                }
                for city in cities.available_catalogs()
            ]
        }

    @app.get("/api/catalogs/{city_slug}")
    async def city_catalog(city_slug: str):
        if not has_catalog(city_slug):
            raise HTTPException(status_code=404, detail="City not found")
        city = get_catalog(city_slug)
        places = [
            {
                "slug": place.slug,
                "title": place.title,
                "summary": place.summary,
                "category": place.category,
                "category_label": city.category_labels.get(place.category, place.category),
                "district": place.district,
                "emoji": place.emoji,
                "visit_minutes": place.visit_minutes,
                "is_free": place.is_free,
                "latitude": place.latitude,
                "longitude": place.longitude,
                "tags": list(place.tags),
                "map_url": google_maps_place_url(place),
            }
            for place in city.places
        ]
        routes = []
        for route in city.routes:
            visible = tuple(
                place
                for slug in route.place_slugs
                if (place := city.place_by_slug(slug)) is not None
            )
            routes.append(
                {
                    "slug": route.slug,
                    "title": route.title,
                    "summary": route.summary,
                    "duration_minutes": route.duration_minutes,
                    "distance_km": route.distance_km,
                    "place_slugs": [place.slug for place in visible],
                    "map_links": [
                        {"url": link.url, "mode": link.mode}
                        for link in google_maps_route_links(visible)
                    ],
                }
            )
        return {
            "slug": city.slug,
            "name": city.name,
            "category_labels": city.category_labels,
            "places": places,
            "routes": routes,
        }

    @app.get("/api/me")
    async def my_city(x_telegram_init_data: str | None = Header(default=None)):
        user_id = authenticated_user(x_telegram_init_data)
        selected = await cities.selected_for_user(user_id)
        return {"city_slug": selected.slug if selected is not None else None}

    @app.post("/api/me/city")
    async def set_my_city(
        body: CitySelection,
        x_telegram_init_data: str | None = Header(default=None),
    ):
        user_id = authenticated_user(x_telegram_init_data)
        if not has_catalog(body.city_slug):
            raise HTTPException(status_code=404, detail="City not found")
        selected = await cities.set_for_user(user_id, body.city_slug)
        return {"city_slug": selected.slug, "city_name": selected.name}

    async def require_active_city(user_id: int, city_slug: str):
        if not has_catalog(city_slug):
            raise HTTPException(status_code=404, detail="City not found")
        selected = await cities.selected_for_user(user_id)
        if selected is None or selected.slug != city_slug:
            raise HTTPException(
                status_code=409,
                detail="Select this city before editing favorites",
            )
        return selected

    @app.get("/api/me/favorites/{city_slug}")
    async def my_favorites(
        city_slug: str,
        x_telegram_init_data: str | None = Header(default=None),
    ):
        user_id = authenticated_user(x_telegram_init_data)
        catalog = await require_active_city(user_id, city_slug)
        stored = await favorites.list_place_slugs(user_id, catalog.slug)
        valid = [
            slug for slug in stored if catalog.place_by_slug(slug) is not None
        ]
        return {"city_slug": catalog.slug, "place_slugs": valid}

    @app.put("/api/me/favorites/{city_slug}/{place_slug}")
    async def add_favorite(
        city_slug: str,
        place_slug: str,
        x_telegram_init_data: str | None = Header(default=None),
    ):
        user_id = authenticated_user(x_telegram_init_data)
        catalog = await require_active_city(user_id, city_slug)
        if catalog.place_by_slug(place_slug) is None:
            raise HTTPException(status_code=404, detail="Place not found")
        await favorites.add(user_id, catalog.slug, place_slug)
        return {"city_slug": catalog.slug, "place_slug": place_slug, "is_favorite": True}

    @app.delete("/api/me/favorites/{city_slug}/{place_slug}")
    async def remove_favorite(
        city_slug: str,
        place_slug: str,
        x_telegram_init_data: str | None = Header(default=None),
    ):
        user_id = authenticated_user(x_telegram_init_data)
        catalog = await require_active_city(user_id, city_slug)
        if catalog.place_by_slug(place_slug) is None:
            raise HTTPException(status_code=404, detail="Place not found")
        await favorites.remove(user_id, catalog.slug, place_slug)
        return {"city_slug": catalog.slug, "place_slug": place_slug, "is_favorite": False}

    @app.post("/api/routes/{city_slug}/preview")
    async def preview_generated_route(
        city_slug: str,
        body: RouteBuildRequest,
        x_telegram_init_data: str | None = Header(default=None),
    ):
        if not has_catalog(city_slug):
            raise HTTPException(status_code=404, detail="City not found")
        excluded: tuple[str, ...] = ()
        if body.exclude_visited:
            user_id = authenticated_user(x_telegram_init_data)
            await require_active_city(user_id, city_slug)
            excluded = await visited.list_place_slugs(user_id, city_slug)
        catalog = get_catalog(city_slug)
        route = build_miniapp_route(catalog, body, excluded_slugs=excluded)
        if route is None:
            raise HTTPException(
                status_code=422, detail="No route fits the selected conditions"
            )
        return route_preview(catalog, route)

    @app.post("/api/me/routes/{city_slug}/save")
    async def save_built_route(
        city_slug: str,
        body: SaveBuiltRouteRequest,
        x_telegram_init_data: str | None = Header(default=None),
    ):
        user_id = authenticated_user(x_telegram_init_data)
        await require_active_city(user_id, city_slug)
        excluded = (
            await visited.list_place_slugs(user_id, city_slug)
            if body.exclude_visited else ()
        )
        catalog = get_catalog(city_slug)
        route = build_miniapp_route(catalog, body, excluded_slugs=excluded)
        if route is None:
            raise HTTPException(
                status_code=409, detail="The route is no longer available"
            )
        preview = route_preview(catalog, route)
        if body.expected_route_id != preview["route_id"]:
            raise HTTPException(
                status_code=409,
                detail="The route changed; generate it again before saving",
            )
        saved = await saved_routes.save(
            user_id, city_slug, route.interest, route.budget_minutes,
            tuple(place.slug for place in route.places),
        )
        return {
            "city_slug": city_slug,
            "route_id": saved.route_id,
            "saved": True,
            "place_count": len(saved.place_slugs),
        }

    @app.get("/api/me/guide/{city_slug}")
    async def guide_dashboard(
        city_slug: str,
        x_telegram_init_data: str | None = Header(default=None),
    ):
        user_id = authenticated_user(x_telegram_init_data)
        await require_active_city(user_id, city_slug)
        return await my_guide_snapshot(
            user_id,
            get_catalog(city_slug),
            favorites=favorites,
            visited=visited,
            saved_routes=saved_routes,
            completed_routes=completed_routes,
        )

    @app.put("/api/me/visited/{city_slug}/{place_slug}")
    async def mark_visited(
        city_slug: str,
        place_slug: str,
        x_telegram_init_data: str | None = Header(default=None),
    ):
        user_id = authenticated_user(x_telegram_init_data)
        catalog = await require_active_city(user_id, city_slug)
        if catalog.place_by_slug(place_slug) is None:
            raise HTTPException(status_code=404, detail="Place not found")
        await visited.add(user_id, city_slug, place_slug)
        return {"city_slug": city_slug, "place_slug": place_slug, "is_visited": True}

    @app.delete("/api/me/visited/{city_slug}/{place_slug}")
    async def unmark_visited(
        city_slug: str,
        place_slug: str,
        x_telegram_init_data: str | None = Header(default=None),
    ):
        user_id = authenticated_user(x_telegram_init_data)
        catalog = await require_active_city(user_id, city_slug)
        if catalog.place_by_slug(place_slug) is None:
            raise HTTPException(status_code=404, detail="Place not found")
        await visited.remove(user_id, city_slug, place_slug)
        return {"city_slug": city_slug, "place_slug": place_slug, "is_visited": False}

    @app.delete("/api/me/saved-routes/{city_slug}/{route_id}")
    async def remove_saved_route(
        city_slug: str,
        route_id: str,
        x_telegram_init_data: str | None = Header(default=None),
    ):
        user_id = authenticated_user(x_telegram_init_data)
        await require_active_city(user_id, city_slug)
        route = await saved_routes.get(user_id, city_slug, route_id)
        if route is None:
            raise HTTPException(status_code=404, detail="Saved route not found")
        await saved_routes.remove(user_id, city_slug, route_id)
        # Completed history is intentionally retained by the existing storage model.
        return {"city_slug": city_slug, "route_id": route_id, "deleted": True}

    @app.put("/api/me/saved-routes/{city_slug}/{route_id}/complete")
    async def mark_route_complete(
        city_slug: str,
        route_id: str,
        x_telegram_init_data: str | None = Header(default=None),
    ):
        user_id = authenticated_user(x_telegram_init_data)
        await require_active_city(user_id, city_slug)
        result = await complete_saved_route(
            user_id=user_id,
            city_slug=city_slug,
            route_id=route_id,
            saved_routes=saved_routes,
            visited=visited,
            catalog=get_catalog(city_slug),
            completed_routes=completed_routes,
        )
        if result is None:
            raise HTTPException(status_code=404, detail="Saved route not found")
        return {
            "city_slug": city_slug,
            "route_id": route_id,
            "added": result.added,
            "already_visited": result.already_visited,
            "unavailable": result.unavailable,
            "already_completed": result.already_completed,
        }

    return app


app = create_miniapp()

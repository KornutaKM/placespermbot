"""Read-only city catalog API with signed Telegram identity for preferences."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.catalog import get_catalog, has_catalog, list_catalogs
from app.catalog_service import CatalogService
from app.config import Settings, get_settings
from app.maps import google_maps_place_url, google_maps_route_links
from app.miniapp_auth import InvalidTelegramInitData, validate_init_data
from app.storage import UserCityRepository

STATIC_DIR = Path(__file__).resolve().parent / "miniapp_static"


class CitySelection(BaseModel):
    city_slug: str = Field(min_length=1, max_length=80)


def create_miniapp(settings: Settings | None = None) -> FastAPI:
    config = settings if settings is not None else get_settings()
    cities = CatalogService(
        default_city_slug=config.city_slug,
        user_city_repo=UserCityRepository(config.database_path),
    )
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
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Content-Security-Policy"] = (
            "default-src 'none'; "
            "script-src 'self' https://telegram.org; "
            "style-src 'self'; "
            "img-src 'self' data:; "
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

    return app


app = create_miniapp()

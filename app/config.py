from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = ""
    environment: str = "development"
    city_slug: str = "saint-petersburg"
    database_path: str = "data/places.db"
    sputnik8_affiliate_url: str = ""
    tripster_affiliate_url: str = ""
    yandex_afisha_url: str = ""
    kudago_events_url: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="PLACES_",
        extra="ignore",
    )

    def require_bot_token(self) -> str:
        token = self.bot_token.strip()
        if not token or token == "replace-me":
            raise RuntimeError("PLACES_BOT_TOKEN is not configured")
        return token


@lru_cache
def get_settings() -> Settings:
    return Settings()

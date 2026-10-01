from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

from app.catalog import get_catalog
from app.config import Settings
from app.database_contract import validate_database_contract


def validate_static_runtime(settings: Settings) -> None:
    settings.require_bot_token()

    catalog = get_catalog(settings.city_slug)
    if not catalog.places:
        raise RuntimeError("Active city catalog is empty")


async def validate_health(settings: Settings) -> None:
    validate_static_runtime(settings)

    database_path = Path(settings.database_path)
    if not database_path.is_file():
        raise RuntimeError("Database is not initialized")

    def validate() -> None:
        try:
            with sqlite3.connect(
                f"file:{database_path}?mode=ro",
                uri=True,
            ) as database:
                validate_database_contract(database, subject="Database")
        except sqlite3.DatabaseError as error:
            raise RuntimeError("Database is not a valid SQLite database") from error

    await asyncio.to_thread(validate)

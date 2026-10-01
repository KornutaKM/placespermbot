import asyncio
import sqlite3

import pytest

from app.database import LATEST_SCHEMA_VERSION, migrate_database
from app.database_backup import create_database_backup
from app.storage import FavoritesRepository


def test_online_backup_is_consistent_and_restorable(tmp_path) -> None:
    async def scenario() -> None:
        source = tmp_path / "live.db"
        destination = tmp_path / "backups" / "snapshot.db"
        await migrate_database(source)
        favorites = FavoritesRepository(str(source))
        await favorites.add(42, "saint-petersburg", "hermitage")

        result = await create_database_backup(source, destination)

        assert result == destination.resolve()
        with sqlite3.connect(destination) as database:
            integrity = database.execute("PRAGMA integrity_check").fetchone()
            favorite = database.execute(
                """
                SELECT user_id, city_slug, place_slug
                FROM favorites
                """
            ).fetchone()
            version = database.execute(
                "SELECT MAX(version) FROM schema_migrations"
            ).fetchone()

        assert integrity == ("ok",)
        assert favorite == (42, "saint-petersburg", "hermitage")
        assert version == (LATEST_SCHEMA_VERSION,)

        restored = FavoritesRepository(str(destination))
        assert await restored.list_place_slugs(
            42,
            "saint-petersburg",
        ) == ("hermitage",)

    asyncio.run(scenario())


def test_backup_does_not_overwrite_live_database(tmp_path) -> None:
    async def scenario() -> None:
        source = tmp_path / "live.db"
        await migrate_database(source)

        with pytest.raises(ValueError, match="must differ"):
            await create_database_backup(source, source)

    asyncio.run(scenario())


def test_backup_rejects_missing_source(tmp_path) -> None:
    async def scenario() -> None:
        with pytest.raises(RuntimeError, match="does not exist"):
            await create_database_backup(
                tmp_path / "missing.db",
                tmp_path / "backup.db",
            )

    asyncio.run(scenario())

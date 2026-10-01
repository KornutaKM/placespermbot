import asyncio
import sqlite3

import pytest

from app.database import LATEST_SCHEMA_VERSION, migrate_database
from app.database_backup import create_database_backup
from app.database_restore import restore_database_backup
from app.storage import FavoritesRepository


def test_restore_replaces_database_atomically(tmp_path) -> None:
    async def scenario() -> None:
        source = tmp_path / "source.db"
        backup = tmp_path / "backup.db"
        destination = tmp_path / "live.db"

        await migrate_database(source)
        source_favorites = FavoritesRepository(str(source))
        await source_favorites.add(7, "moscow", "red-square")
        await create_database_backup(source, backup)

        await migrate_database(destination)
        live_favorites = FavoritesRepository(str(destination))
        await live_favorites.add(8, "kazan", "kremlin")

        result = await restore_database_backup(backup, destination)

        assert result == destination.resolve()
        restored = FavoritesRepository(str(destination))
        assert await restored.list_place_slugs(7, "moscow") == ("red-square",)
        assert await restored.list_place_slugs(8, "kazan") == ()

    asyncio.run(scenario())


def test_restore_rejects_corrupt_backup_without_touching_live_database(tmp_path) -> None:
    async def scenario() -> None:
        backup = tmp_path / "corrupt.db"
        backup.write_bytes(b"not a sqlite database")
        destination = tmp_path / "live.db"
        await migrate_database(destination)
        favorites = FavoritesRepository(str(destination))
        await favorites.add(42, "saint-petersburg", "hermitage")

        with pytest.raises(RuntimeError, match="valid SQLite"):
            await restore_database_backup(backup, destination)

        assert await favorites.list_place_slugs(
            42,
            "saint-petersburg",
        ) == ("hermitage",)

    asyncio.run(scenario())


def test_restore_rejects_newer_schema_without_touching_live_database(tmp_path) -> None:
    async def scenario() -> None:
        backup = tmp_path / "future.db"
        await migrate_database(backup)
        with sqlite3.connect(backup) as database:
            database.execute(
                """
                INSERT INTO schema_migrations (version, name)
                VALUES (?, 'future')
                """,
                (LATEST_SCHEMA_VERSION + 1,),
            )
            database.commit()

        destination = tmp_path / "live.db"
        await migrate_database(destination)
        favorites = FavoritesRepository(str(destination))
        await favorites.add(9, "sochi", "arboretum")

        with pytest.raises(RuntimeError, match="newer than this app"):
            await restore_database_backup(backup, destination)

        assert await favorites.list_place_slugs(9, "sochi") == ("arboretum",)

    asyncio.run(scenario())


def test_restore_rejects_incomplete_migration_history(tmp_path) -> None:
    async def scenario() -> None:
        backup = tmp_path / "incomplete.db"
        await migrate_database(backup)
        with sqlite3.connect(backup) as database:
            database.execute(
                "DELETE FROM schema_migrations WHERE version = ?",
                (LATEST_SCHEMA_VERSION,),
            )
            database.commit()

        with pytest.raises(RuntimeError, match="migrations are incomplete"):
            await restore_database_backup(backup, tmp_path / "live.db")

        assert not (tmp_path / "live.db").exists()

    asyncio.run(scenario())


def test_restore_rejects_tampered_migration_name(tmp_path) -> None:
    async def scenario() -> None:
        backup = tmp_path / "tampered.db"
        await migrate_database(backup)
        with sqlite3.connect(backup) as database:
            database.execute(
                "UPDATE schema_migrations SET name = 'tampered' WHERE version = 6"
            )
            database.commit()

        destination = tmp_path / "live.db"
        await migrate_database(destination)
        favorites = FavoritesRepository(str(destination))
        await favorites.add(11, "perm", "esplanade")

        with pytest.raises(RuntimeError, match="migration metadata is inconsistent"):
            await restore_database_backup(backup, destination)

        assert await favorites.list_place_slugs(11, "perm") == ("esplanade",)

    asyncio.run(scenario())

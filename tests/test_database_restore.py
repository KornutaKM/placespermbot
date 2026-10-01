import asyncio
import sqlite3
from unittest.mock import patch

import pytest

from app.database import LATEST_SCHEMA_VERSION, migrate_database
from app.database_backup import create_database_backup
from app.database_restore import restore_database_backup
from app.storage import FavoritesRepository, SavedRoutesRepository


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


def test_restore_rejects_missing_table_without_touching_live_database(tmp_path) -> None:
    async def scenario() -> None:
        backup = tmp_path / "missing-table.db"
        await migrate_database(backup)
        with sqlite3.connect(backup) as database:
            database.execute("DROP TABLE completed_route_snapshots")
            database.commit()

        destination = tmp_path / "live.db"
        await migrate_database(destination)
        favorites = FavoritesRepository(str(destination))
        await favorites.add(12, "moscow", "red-square")

        with pytest.raises(RuntimeError, match="Backup schema is incomplete"):
            await restore_database_backup(backup, destination)

        assert await favorites.list_place_slugs(12, "moscow") == ("red-square",)

    asyncio.run(scenario())


def test_restore_rejects_missing_column_without_touching_live_database(tmp_path) -> None:
    async def scenario() -> None:
        backup = tmp_path / "missing-column.db"
        await migrate_database(backup)
        with sqlite3.connect(backup) as database:
            database.execute("ALTER TABLE saved_routes DROP COLUMN created_at")
            database.commit()

        destination = tmp_path / "live.db"
        await migrate_database(destination)
        favorites = FavoritesRepository(str(destination))
        await favorites.add(13, "perm", "esplanade")

        with pytest.raises(RuntimeError, match="saved_routes is incomplete"):
            await restore_database_backup(backup, destination)

        assert await favorites.list_place_slugs(13, "perm") == ("esplanade",)

    asyncio.run(scenario())


def test_restore_rejects_invalid_storage_type_without_touching_live_database(
    tmp_path,
) -> None:
    async def scenario() -> None:
        backup = tmp_path / "invalid-type.db"
        await migrate_database(backup)
        with sqlite3.connect(backup) as database:
            database.execute(
                """
                INSERT INTO favorites (user_id, city_slug, place_slug)
                VALUES (?, ?, ?)
                """,
                ("not-an-integer", "perm", "esplanade"),
            )
            database.commit()

        destination = tmp_path / "live.db"
        await migrate_database(destination)
        favorites = FavoritesRepository(str(destination))
        await favorites.add(15, "moscow", "red-square")

        with pytest.raises(RuntimeError, match="values with invalid storage types"):
            await restore_database_backup(backup, destination)

        assert await favorites.list_place_slugs(15, "moscow") == ("red-square",)

    asyncio.run(scenario())


def test_restore_rejects_tampered_route_snapshot_without_touching_live_database(
    tmp_path,
) -> None:
    async def scenario() -> None:
        backup = tmp_path / "tampered-route.db"
        await migrate_database(backup)
        saved_routes = SavedRoutesRepository(str(backup))
        route = await saved_routes.save(
            31,
            "saint-petersburg",
            "classic",
            120,
            ("hermitage", "russian-museum"),
        )
        with sqlite3.connect(backup) as database:
            database.execute(
                """
                UPDATE saved_routes
                SET place_slugs_json = ?
                WHERE route_id = ?
                """,
                ('["hermitage","summer-garden"]', route.route_id),
            )
            database.commit()

        destination = tmp_path / "live.db"
        await migrate_database(destination)
        favorites = FavoritesRepository(str(destination))
        await favorites.add(31, "moscow", "red-square")

        with pytest.raises(RuntimeError, match="id does not match"):
            await restore_database_backup(backup, destination)

        assert await favorites.list_place_slugs(31, "moscow") == ("red-square",)

    asyncio.run(scenario())


def test_restore_removes_sidecars_before_fsyncing_parent_directory(tmp_path) -> None:
    async def scenario() -> None:
        backup = tmp_path / "backup.db"
        destination = tmp_path / "data" / "live.db"
        await migrate_database(backup)
        destination.parent.mkdir(parents=True, exist_ok=True)

        for suffix in ("-wal", "-shm", "-journal"):
            (destination.parent / f"{destination.name}{suffix}").write_bytes(b"stale")

        def assert_sidecars_removed(path) -> None:
            assert path == destination.parent.resolve()
            for suffix in ("-wal", "-shm", "-journal"):
                assert not (destination.parent / f"{destination.name}{suffix}").exists()

        with patch(
            "app.database_restore.fsync_directory",
            side_effect=assert_sidecars_removed,
        ) as sync_directory:
            await restore_database_backup(backup, destination)

        sync_directory.assert_called_once_with(destination.parent.resolve())

    asyncio.run(scenario())

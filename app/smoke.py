"""Offline packaged-image smoke: imports, catalog, SQLite backup/restore."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from app import main as main_module
from app.config import Settings, get_settings
from app.database import migrate_database
from app.database_backup import create_database_backup
from app.database_restore import restore_database_backup
from app.runtime_checks import validate_health, validate_static_runtime


async def validate_packaged_storage(settings: Settings) -> None:
    """Exercise real migrations, health, backup, and restore in an isolated temp dir."""
    with tempfile.TemporaryDirectory(prefix="places-packaged-smoke-") as temporary:
        root = Path(temporary)
        live = root / "database.db"
        backup = root / "backups" / "snapshot.db"
        restored = root / "recovered.db"

        await migrate_database(live)
        await validate_health(settings.model_copy(update={"database_path": str(live)}))
        await create_database_backup(live, backup)
        await restore_database_backup(backup, restored)
        await validate_health(settings.model_copy(update={"database_path": str(restored)}))


def main() -> None:
    settings = get_settings()
    validate_static_runtime(settings)
    if not callable(main_module.main):
        raise TypeError("app.main entrypoint is unavailable")
    asyncio.run(validate_packaged_storage(settings))
    print("smoke: ok")


if __name__ == "__main__":
    main()

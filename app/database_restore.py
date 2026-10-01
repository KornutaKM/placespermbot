from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

from app.database import validate_migration_ledger


def _validate_backup(path: Path) -> None:
    if not path.is_file():
        raise RuntimeError("Backup database does not exist")

    try:
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as database:
            integrity = database.execute("PRAGMA integrity_check").fetchone()
            if integrity != ("ok",):
                raise RuntimeError("Backup database failed integrity check")

            table = database.execute(
                """
                SELECT 1 FROM sqlite_master
                WHERE type = 'table' AND name = 'schema_migrations'
                """
            ).fetchone()
            if table is None:
                raise RuntimeError("Backup database has no migration metadata")

            rows = database.execute(
                "SELECT version, name FROM schema_migrations ORDER BY version"
            ).fetchall()
    except sqlite3.DatabaseError as error:
        raise RuntimeError("Backup is not a valid SQLite database") from error

    validate_migration_ledger(
        [(int(row[0]), str(row[1])) for row in rows],
        subject="Backup",
        require_complete=True,
    )


def _restore_database(backup: Path, destination: Path) -> None:
    _validate_backup(backup)
    destination.parent.mkdir(parents=True, exist_ok=True)

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=f".{destination.name}.restore-",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            with backup.open("rb") as source:
                shutil.copyfileobj(source, temporary)
            temporary.flush()
            os.fsync(temporary.fileno())

        _validate_backup(temporary_path)
        os.replace(temporary_path, destination)
        temporary_path = None

        for suffix in ("-wal", "-shm"):
            Path(f"{destination}{suffix}").unlink(missing_ok=True)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


async def restore_database_backup(
    backup_path: str | Path,
    destination_path: str | Path,
) -> Path:
    backup = Path(backup_path).resolve()
    destination = Path(destination_path).resolve()
    if backup == destination:
        raise ValueError("Backup source must differ from restore destination")

    await asyncio.to_thread(_restore_database, backup, destination)
    return destination


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate and atomically restore a SQLite backup.",
    )
    parser.add_argument("backup", help="Path to a SQLite backup")
    parser.add_argument("destination", help="Path to the stopped app database")
    return parser


async def _main() -> None:
    args = _parser().parse_args()
    destination = await restore_database_backup(args.backup, args.destination)
    print(destination)


if __name__ == "__main__":
    asyncio.run(_main())

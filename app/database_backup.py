from __future__ import annotations

import argparse
import asyncio
import os
import sqlite3
import tempfile
from pathlib import Path


def _backup_database(source: Path, destination: Path) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=f".{destination.name}.backup-",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)

        with (
            sqlite3.connect(f"file:{source}?mode=ro", uri=True) as source_database,
            sqlite3.connect(temporary_path) as destination_database,
        ):
            source_database.backup(destination_database)
            row = destination_database.execute("PRAGMA integrity_check").fetchone()
            if row != ("ok",):
                raise RuntimeError("SQLite backup failed integrity check")

        with temporary_path.open("rb") as backup_file:
            os.fsync(backup_file.fileno())

        os.replace(temporary_path, destination)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


async def create_database_backup(
    source_path: str | Path,
    destination_path: str | Path,
) -> Path:
    source = Path(source_path).resolve()
    destination = Path(destination_path).resolve()
    if not source.is_file():
        raise RuntimeError("Source database does not exist")
    if source == destination:
        raise ValueError("Backup destination must differ from source database")

    destination.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(_backup_database, source, destination)
    return destination


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a consistent online SQLite backup.",
    )
    parser.add_argument("source", help="Path to the live SQLite database")
    parser.add_argument("destination", help="Path for the backup database")
    return parser


async def _main() -> None:
    args = _parser().parse_args()
    destination = await create_database_backup(args.source, args.destination)
    print(destination)


if __name__ == "__main__":
    asyncio.run(_main())

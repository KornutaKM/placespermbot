from __future__ import annotations

import argparse
import asyncio
import sqlite3
from pathlib import Path


def _backup_database(source: Path, destination: Path) -> None:
    with sqlite3.connect(source) as source_database:
        with sqlite3.connect(destination) as destination_database:
            source_database.backup(destination_database)
            row = destination_database.execute("PRAGMA integrity_check").fetchone()
            if row != ("ok",):
                raise RuntimeError("SQLite backup failed integrity check")


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

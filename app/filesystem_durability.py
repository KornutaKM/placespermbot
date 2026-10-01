from __future__ import annotations

import os
from pathlib import Path


def fsync_directory(path: str | Path) -> None:
    directory = Path(path)
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)

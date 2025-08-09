from __future__ import annotations

import uuid
import shutil
from pathlib import Path


def ensure_dir(path: Path) -> Path:
    """Ensure directory exists and return it."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def disk_free_gb(path: Path) -> float:
    """Return free disk space in gigabytes for the given path."""
    usage = shutil.disk_usage(path)
    return round(usage.free / (1024 ** 3), 2)


def get_dir_size_mb(path: Path) -> float:
    """Return total directory size in megabytes."""
    total = 0
    if path.exists():
        for p in path.rglob('*'):
            if p.is_file():
                total += p.stat().st_size
    return round(total / (1024 ** 2), 2)


def uuid_filename(suffix: str = '.wav') -> str:
    """Generate a UUID filename with the given suffix."""
    return f"{uuid.uuid4()}{suffix}"

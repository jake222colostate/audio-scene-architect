from __future__ import annotations
import uuid, shutil
from pathlib import Path

def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True); return path

def disk_free_gb(path: Path) -> float:
    usage = shutil.disk_usage(path)
    return round(usage.free / (1024**3), 2)

def get_dir_size_mb(path: Path) -> float:
    total = 0
    if path.exists():
        for p in path.rglob('*'):
            if p.is_file():
                total += p.stat().st_size
    return round(total / (1024**2), 2)

def uuid_filename(suffix: str = ".wav") -> str:
    return f"{uuid.uuid4()}{suffix}"

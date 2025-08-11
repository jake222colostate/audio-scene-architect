# backend/services/state.py
from __future__ import annotations
import os
import time
from collections import deque
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Deque, Dict, Any

START_TIME = time.time()
RECENT: Deque[Dict[str, Any]] = deque(maxlen=10)


def record_generation(entry: Dict[str, Any]) -> None:
    RECENT.appendleft(entry)


def uptime_seconds() -> int:
    return int(time.time() - START_TIME)


def dir_size_mb(path: Path) -> float:
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total += (Path(root) / f).stat().st_size
            except Exception:
                pass
    return round(total / (1024 * 1024), 3)
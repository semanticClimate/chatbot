"""Shared pytest configuration: repo root + backend.app on sys.path."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLIMATE = ROOT / "backend.app"

for path in (ROOT, CLIMATE):
    entry = str(path)
    if entry not in sys.path:
        sys.path.insert(0, entry)

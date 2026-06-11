"""System prompt template from disk."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=8)
def load_system_prompt_template(prompt_path: Path) -> str:
    return prompt_path.read_text(encoding="utf-8")

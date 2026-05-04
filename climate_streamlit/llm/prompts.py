"""System prompt template from disk."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def load_system_prompt_template(base_dir: Path) -> str:
    p = base_dir / "prompts" / "system_rag_json.txt"
    return p.read_text(encoding="utf-8")

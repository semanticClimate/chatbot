"""
Shared constants for HTML section parsing, paragraph chunking, and highlight
annotation.

This module keeps the "magic values" in one place so the parser, annotator, and
numbering code stay in sync.
"""

from __future__ import annotations

import re

HEADING_TAGS = tuple(f"h{i}" for i in range(1, 7))
MAX_OUTLINE_DEPTH = 6

_SKIP_H1_IDS = {"section", "contents", "section-3", "section-4", "section-5"}
_SKIP_H1_TEXT_RE = re.compile(r"^\s*$|description automatically generated|logo with text", re.I)

# Minimum meaningful paragraph length (characters). Shorter paragraphs are
# merged with the previous one so we don't create empty/trivial chunks.
MIN_PARA_CHARS = 40

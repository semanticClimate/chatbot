"""
Backward-compatible facade for HTML sectioning.

This file intentionally keeps the original import path alive:
`backend.app.html_sectioning`.

All real logic lives in `backend.app.html_sectioning_core`, which is split
by responsibility so the parser, chunker, annotator, and numbering code can be
maintained independently.

Future work:
- Move any remaining legacy-only helpers out of the facade.
- Add tests that compare the old and new package outputs on the same HTML.
"""

from __future__ import annotations

# from backend.app.html_sectioning_core import *  # noqa: F401,F403
from __future__ import annotations

from .html_sectioning_core.helpers import load_html_file
from .html_sectioning_core.parsing import parse_book_html
from .html_sectioning_core.chunking import (
    parse_html_to_paragraph_chunks,
    records_to_indexed_chunks,
    word_chunks,
)
from .html_sectioning_core.legacy import (
    format_passage_for_prompt,
    parse_html_path_to_chunks,
)
from .html_sectioning_core.annotation import annotate_html_with_section_ids
from .html_sectioning_core.numbering import annotate_html_with_numbering
from .html_sectioning_core.models import (
    SectionRecord,
    ParagraphChunk,
    IndexedChunk,
)

__all__ = [
    "load_html_file",
    "parse_book_html",
    "parse_html_to_paragraph_chunks",
    "records_to_indexed_chunks",
    "word_chunks",
    "format_passage_for_prompt",
    "parse_html_path_to_chunks",
    "annotate_html_with_section_ids",
    "annotate_html_with_numbering",
    "SectionRecord",
    "ParagraphChunk",
    "IndexedChunk",
]
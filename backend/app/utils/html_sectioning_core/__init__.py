"""
Public exports for the html_sectioning_core package.

This package is the refactored implementation behind the compatibility facade
`backend.app.html_sectioning`.
"""

from .annotation import annotate_html_with_section_ids
from .chunking import parse_html_to_paragraph_chunks, records_to_indexed_chunks, word_chunks
from .legacy import format_passage_for_prompt, parse_html_path_to_chunks
from .models import IndexedChunk, ParagraphChunk, SectionRecord
from .numbering import annotate_html_with_numbering
from .parsing import parse_book_html

__all__ = [
    "annotate_html_with_section_ids",
    "annotate_html_with_numbering",
    "format_passage_for_prompt",
    "IndexedChunk",
    "ParagraphChunk",
    "parse_book_html",
    "parse_html_path_to_chunks",
    "parse_html_to_paragraph_chunks",
    "records_to_indexed_chunks",
    "SectionRecord",
    "word_chunks",
]

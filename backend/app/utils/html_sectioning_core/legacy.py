"""
Legacy compatibility helpers for older callers.

These helpers preserve the old public API used by app code and scripts while the
new paragraph-aware pipeline lives in the dedicated chunking module.
"""

from __future__ import annotations

from typing import List

from .chunking import parse_html_to_paragraph_chunks, records_to_indexed_chunks, word_chunks
from .models import IndexedChunk

def format_passage_for_prompt(section_number: str, section_title: str, body: str, paragraph_number: str = "") -> str:
    """Format a passage for the LLM prompt while preserving legacy call sites."""
    t = body.strip()
    if t.startswith("[§"):
        return t
    line = f"[§ {section_number}"
    if section_title:
        line += f" — {section_title}"
    if paragraph_number:
        line += f" | ¶ {paragraph_number}"
    line += "]"
    return f"{line}\n{t}"

def parse_html_path_to_chunks(path, chunk_size: int, chunk_overlap: int) -> List[IndexedChunk]:
    """
    Legacy entry point that now delegates to paragraph-aware chunking.

    Note: chunk_size and chunk_overlap are retained for API compatibility but are
    no longer used because each paragraph becomes one chunk.
    """
    para_chunks = parse_html_to_paragraph_chunks(path)
    out: List[IndexedChunk] = []
    for pc in para_chunks:
        paragraph_number = f"{pc.section_number}.{pc.para_index + 1}"
        out.append(
            IndexedChunk(
                document=pc.document,
                section_number=pc.section_number,
                section_title=pc.section_title,
                chunk_index=pc.para_index,
                paragraph_number=paragraph_number,
                heading_id=pc.heading_id,
                chunk_id=pc.chunk_id,
                anchor_id=pc.anchor_id,
            )
        )
    return out

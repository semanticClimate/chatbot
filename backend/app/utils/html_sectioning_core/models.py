"""
Data containers used by the HTML sectioning pipeline.

These classes are intentionally small and frozen so they can be safely used in
RAG metadata, tests, and downstream indexing code.
"""

from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class SectionRecord:
    """One section of the book (heading + body text). Used by legacy API."""
    section_number: str
    title: str
    body: str
    level: int
    heading_id: str = ""

@dataclass(frozen=True)
class ParagraphChunk:
    """
    One paragraph = one RAG chunk.

    chunk_id  : unique stable string stored in ChromaDB metadata
    anchor_id : HTML element id used by the viewer to highlight this paragraph
    """
    chunk_id: str
    anchor_id: str
    document: str
    section_number: str
    section_title: str
    para_index: int
    heading_id: str = ""

@dataclass(frozen=True)
class IndexedChunk:
    """Backward-compatible chunk container used by older callers."""
    document: str
    section_number: str
    section_title: str
    chunk_index: int
    paragraph_number: str = ""
    heading_id: str = ""
    chunk_id: str = ""
    anchor_id: str = ""

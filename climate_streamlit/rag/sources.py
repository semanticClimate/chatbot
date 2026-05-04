"""Turn retrieved chunks into numbered source records for the LLM and UI."""

from __future__ import annotations

from typing import Optional

from config_loader import AppSettings
from pdf.text import make_pdf_search_query


def build_sources(
    chunks: list[dict],
    settings: AppSettings,
    pdf_chunk_map: Optional[dict] = None,
) -> list[dict]:
    """Create unique ordered source list from retrieved chunks."""
    seen = set()
    sources = []
    pdf_chunk_map = pdf_chunk_map or {}
    for c in chunks:
        chunk_id = c.get("chunk_id", "")
        if not chunk_id or chunk_id in seen:
            continue
        seen.add(chunk_id)
        pdf_map = pdf_chunk_map.get(chunk_id, {})
        raw_match = pdf_map.get("match_text", "") or c.get("document", "")
        sources.append({
            "source_id": len(sources) + 1,
            "chunk_id": chunk_id,
            "anchor_id": c.get("anchor_id", ""),
            "section_number": c.get("section_number", ""),
            "section_title": c.get("section_title", ""),
            "heading_id": c.get("heading_id", ""),
            "document": c.get("document", ""),
            "pdf_page": pdf_map.get("page", 1),
            "pdf_bbox": pdf_map.get("bbox"),
            "pdf_query": make_pdf_search_query(raw_match, settings.pdf_max_query_words),
        })
    return sources

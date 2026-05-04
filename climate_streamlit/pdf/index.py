"""PDF page index and chunk→page mapping."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import fitz
import streamlit as st

from pdf.text import keyword_set, norm_text


@st.cache_resource
def load_pdf_index(pdf_path: str) -> list[dict[str, Any]]:
    doc = fitz.open(pdf_path)
    pages: list[dict[str, Any]] = []
    for i, page in enumerate(doc):
        blocks = []
        for b in page.get_text("blocks"):
            if len(b) < 5:
                continue
            x0, y0, x1, y1, text = b[:5]
            t = (text or "").strip()
            if len(t) < 25:
                continue
            blocks.append({
                "text": t,
                "norm": norm_text(t),
                "bbox": [float(x0), float(y0), float(x1), float(y1)],
            })

        page_text = page.get_text("text") or ""
        pages.append({
            "page": i + 1,
            "norm": norm_text(page_text),
            "blocks": blocks,
        })
    doc.close()
    return pages


def best_page_and_block(chunk_text: str, pdf_index: list[dict], pdf_keyword_max_words: int) -> dict:
    chunk_keywords = keyword_set(chunk_text, pdf_keyword_max_words)
    chunk_norm = norm_text(chunk_text)
    if not chunk_norm:
        return {"page": 1, "bbox": None, "match_text": ""}

    best_page: dict[str, Any] = {"page": 1, "score": -1.0, "blocks": []}
    for p in pdf_index:
        page_norm = p["norm"]
        if not page_norm:
            continue
        if chunk_keywords:
            page_words = set(page_norm.split(" "))
            overlap = len(chunk_keywords.intersection(page_words))
            score = overlap / max(1, len(chunk_keywords))
        else:
            score = 0.0
        if score > best_page["score"]:
            best_page = {"page": p["page"], "score": score, "blocks": p["blocks"]}

    best_block: dict[str, Any] = {"score": -1.0, "bbox": None, "text": ""}
    for b in best_page["blocks"]:
        block_norm = b["norm"]
        if not block_norm:
            continue
        if chunk_keywords:
            block_words = set(block_norm.split(" "))
            overlap = len(chunk_keywords.intersection(block_words))
            score = overlap / max(1, len(chunk_keywords))
        else:
            score = 0.0
        if score > best_block["score"]:
            best_block = {"score": score, "bbox": b["bbox"], "text": b["text"]}

    return {
        "page": int(best_page["page"]),
        "bbox": best_block["bbox"],
        "match_text": best_block["text"] or chunk_text,
    }


@st.cache_data
def map_chunks_to_pdf(
    chunks: list[dict],
    pdf_path: str,
    pdf_keyword_max_words: int,
) -> dict:
    """Streamlit cache key includes primitive args; pass keyword max from settings."""
    if not Path(pdf_path).is_file():
        return {}
    pdf_index = load_pdf_index(pdf_path)
    mapped = {}
    for c in chunks:
        chunk_id = c.get("chunk_id", "")
        if not chunk_id:
            continue
        mapped[chunk_id] = best_page_and_block(
            c.get("document", ""),
            pdf_index,
            pdf_keyword_max_words,
        )
    return mapped

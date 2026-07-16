"""
Paragraph-level chunking and legacy word-chunk compatibility helpers.

This module is the main RAG entry point for paragraph-aware indexing. It also
keeps the older word-chunk helpers available for scripts that still import them.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, List, Tuple

from bs4 import BeautifulSoup

from .constants import MIN_PARA_CHARS
from .helpers import (
    _bump_counters,
    _collect_body_until_next_heading,
    _direct_child_tags,
    _format_section_number,
    _heading_level,
    _is_skippable_h1,
    find_book_root,
    load_html_file,
)
from .models import IndexedChunk, ParagraphChunk
from .parsing import _parse_book_html_format_A

def _split_body_into_paragraphs(body_text: str) -> List[str]:
    """
    Split a section body into paragraphs.

    Limitation: this uses text-level blank-line boundaries, which is fine for the
    current HTML export but can be improved later if the HTML contains more
    structural paragraph markers.
    """
    raw_paras = re.split(r"\n{2,}", body_text)
    paras: List[str] = []
    for raw in raw_paras:
        text = raw.strip()
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue
        if paras and len(text) < MIN_PARA_CHARS:
            paras[-1] = paras[-1] + " " + text
        else:
            paras.append(text)
    return paras

def _collect_paragraph_texts_for_section(heading_tag, stop_levels: Tuple[int, ...]) -> List[str]:
    """
    Collect the text of individual block-level children for a flat-heading section.

    Future work: support more HTML block types if the source content changes.
    """
    para_texts: List[str] = []
    current_list: List[str] = []

    def flush_list() -> None:
        if current_list:
            para_texts.append(" ".join(current_list))
            current_list.clear()

    node = heading_tag.next_sibling
    while node is not None:
        if isinstance(node, BeautifulSoup().element.Tag):
            lvl = _heading_level(node)
            if lvl is not None and lvl in stop_levels:
                break
            if node.name == "section" and "footnotes" in node.get("class", []):
                break

            if node.name in ("ul", "ol"):
                flush_list()
                items = [li.get_text(separator=" ", strip=True) for li in node.find_all("li") if li.get_text(strip=True)]
                combined = "; ".join(items)
                if combined:
                    para_texts.append(combined)
            elif node.name == "p":
                flush_list()
                text = node.get_text(separator=" ", strip=True)
                if text:
                    para_texts.append(text)
            elif node.name in ("table", "blockquote", "figure", "div"):
                flush_list()
                text = node.get_text(separator=" ", strip=True)
                if text:
                    para_texts.append(text)
            else:
                text = node.get_text(separator=" ", strip=True)
                if text:
                    current_list.append(text)
        node = node.next_sibling

    flush_list()
    return [re.sub(r"\s+", " ", p).strip() for p in para_texts if p.strip()]

def _section_paragraphs_from_format_B(soup: BeautifulSoup) -> List[Tuple[str, str, str, List[str]]]:
    """Return section metadata and paragraph texts for flat-heading HTML."""
    root = find_book_root(soup)
    all_headings = [
        tag for tag in root.find_all(["h1", "h2", "h3"])
        if not (tag.name == "h1" and _is_skippable_h1(tag))
        and tag.get_text(strip=True)
    ]
    counters: List[int] = [0] * 6
    results = []
    for heading in all_headings:
        level = int(heading.name[1])
        title = heading.get_text(separator=" ", strip=True)
        heading_id = heading.get("id", "")
        stop_levels = tuple(range(1, level + 1))
        paras = _collect_paragraph_texts_for_section(heading, stop_levels)
        if not paras:
            continue
        _bump_counters(counters, level)
        number = _format_section_number(counters, level)
        results.append((number, title, heading_id, paras))
    return results

def parse_html_to_paragraph_chunks(path: Path | str) -> List[ParagraphChunk]:
    """
    Parse book HTML and return one ParagraphChunk per paragraph.

    This is the preferred RAG indexing entry point for the current backend.
    """
    html = load_html_file(path)
    soup = BeautifulSoup(html, "html.parser")
    chunks: List[ParagraphChunk] = []

    if _parse_book_html_format_A.__name__ and False:
        pass

    # Decide format using the same nested-section heuristic as the parser.
    from .parsing import _is_nested_section_format
    if _is_nested_section_format(soup):
        records = _parse_book_html_format_A(soup)
        for rec in records:
            paras = _split_body_into_paragraphs(rec.body)
            for idx, para in enumerate(paras):
                para_n = idx + 1
                chunk_id = f"p-{rec.section_number}-{para_n}"
                anchor_id = f"para-{rec.section_number}-{para_n}"
                header = f"[§ {rec.section_number} — {rec.title}]"
                chunks.append(ParagraphChunk(
                    chunk_id=chunk_id,
                    anchor_id=anchor_id,
                    document=f"{header}\n{para}",
                    section_number=rec.section_number,
                    section_title=rec.title,
                    para_index=idx,
                    heading_id=rec.heading_id,
                ))
    else:
        sections = _section_paragraphs_from_format_B(soup)
        for number, title, heading_id, paras in sections:
            for idx, para in enumerate(paras):
                para_n = idx + 1
                chunk_id = f"p-{number}-{para_n}"
                anchor_id = f"para-{number}-{para_n}"
                header = f"[§ {number} — {title}]"
                chunks.append(ParagraphChunk(
                    chunk_id=chunk_id,
                    anchor_id=anchor_id,
                    document=f"{header}\n{para}",
                    section_number=number,
                    section_title=title,
                    para_index=idx,
                    heading_id=heading_id,
                ))
    return chunks

def word_chunks(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Split text on words using a sliding window."""
    words = text.split()
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be in [0, chunk_size)")
    chunks: List[str] = []
    i = 0
    while i < len(words):
        chunks.append(" ".join(words[i : i + chunk_size]))
        i += chunk_size - overlap
    return chunks

def _split_body_paragraphs(body: str) -> List[str]:
    """Split section body into logical paragraphs using blank-line boundaries."""
    parts = [p.strip() for p in re.split(r"\n\s*\n+", body) if p.strip()]
    if parts:
        return parts
    one = body.strip()
    return [one] if one else []

def records_to_indexed_chunks(records: Iterable, chunk_size: int, chunk_overlap: int) -> List[IndexedChunk]:
    """Legacy helper that turns section records into IndexedChunk instances."""
    out: List[IndexedChunk] = []
    for rec in records:
        chunk_counter = 0
        paragraphs = _split_body_paragraphs(rec.body)
        for paragraph_idx, paragraph in enumerate(paragraphs, start=1):
            paragraph_number = f"{rec.section_number}.{paragraph_idx}"
            for part in word_chunks(paragraph, chunk_size, chunk_overlap):
                header = f"[§ {rec.section_number}"
                if rec.title:
                    header += f" — {rec.title}"
                header += f" | ¶ {paragraph_number}]"
                doc = f"{header}\n{part}"
                out.append(
                    IndexedChunk(
                        document=doc,
                        section_number=rec.section_number,
                        section_title=rec.title,
                        paragraph_number=paragraph_number,
                        chunk_index=chunk_counter,
                    )
                )
                chunk_counter += 1
    return out

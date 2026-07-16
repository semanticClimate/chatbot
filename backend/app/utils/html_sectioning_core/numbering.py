"""
Visible section and paragraph numbering for preview / export HTML.

This is separate from anchor stamping so future changes to display numbering do
not affect the RAG/highlight pipeline.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from bs4 import BeautifulSoup, Tag

from .constants import MAX_OUTLINE_DEPTH
from .helpers import (
    _bump_counters,
    _direct_child_tags,
    _format_section_number,
    find_book_root,
)

def _section_level_from_attr(tag: Tag) -> Optional[int]:
    """Read a numeric outline level from data-outline-level if present."""
    raw = tag.get("data-outline-level")
    if raw is None:
        return None
    try:
        n = int(str(raw).strip())
    except ValueError:
        return None
    if 1 <= n <= MAX_OUTLINE_DEPTH:
        return n
    return None

def _heading_from_direct_content(section: Tag) -> Tuple[Optional[str], Optional[int]]:
    """Find the direct heading tag inside a section for visible numbering."""
    for child in _direct_child_tags(section):
        if child.name == "section":
            continue
        if child.name in tuple(f"h{i}" for i in range(1, 7)):
            text = child.get_text(separator=" ", strip=True)
            if text:
                return text, int(child.name[1])
        for h in child.find_all(tuple(f"h{i}" for i in range(1, 7))):
            parent_sec = h.find_parent("section")
            if parent_sec is section and h.get_text(strip=True):
                return h.get_text(separator=" ", strip=True), int(h.name[1])
    return None, None

def _section_title_and_level(tag: Tag, parent_depth: int, default_child_level: int) -> Tuple[str, int]:
    """Resolve section title and level for display-numbering mode."""
    attr_level = _section_level_from_attr(tag)
    h_title, h_level = _heading_from_direct_content(tag)
    title = h_title or tag.get("aria-label") or ""
    title = " ".join(title.split()).strip()
    if attr_level is not None:
        level = attr_level
    elif h_level is not None:
        level = h_level
    else:
        level = default_child_level
    if level <= parent_depth:
        level = parent_depth + 1
    if level > MAX_OUTLINE_DEPTH:
        level = MAX_OUTLINE_DEPTH
    return title, level

def _prefix_text_once(text: str, prefix: str) -> str:
    """Prefix text once, preserving original formatting when already numbered."""
    stripped = " ".join(text.split()).strip()
    if stripped.startswith(prefix):
        return text
    return f"{prefix} {text}".strip()

def _section_id_from_number(section_number: str) -> str:
    """Convert a dotted section number into a stable HTML id."""
    return f"s{section_number.replace('.', '-')}"

def _paragraph_id_from_section(section_id: str, paragraph_index: int) -> str:
    """Build a paragraph id under a section id."""
    return f"{section_id}_p{paragraph_index}"

def _direct_heading_tag(section: Tag) -> Optional[Tag]:
    """Get the heading tag that directly belongs to this section."""
    for child in _direct_child_tags(section):
        if child.name in tuple(f"h{i}" for i in range(1, 7)):
            return child
        if child.name == "section":
            continue
        nested_heading = child.find(tuple(f"h{i}" for i in range(1, 7)))
        if nested_heading and nested_heading.find_parent("section") is section:
            return nested_heading
    return None

def _direct_paragraph_tags(section: Tag) -> List[Tag]:
    """Return direct paragraph tags that should receive visible numbering."""
    paragraphs: List[Tag] = []
    for child in _direct_child_tags(section):
        if child.name == "section":
            continue
        if child.name == "p":
            paragraphs.append(child)
        paragraphs.extend(p for p in child.find_all("p") if p.find_parent("section") is section)
    return paragraphs

def _annotate_section_tree_for_display(section: Tag, counters: List[int], parent_depth: int) -> None:
    """Recursively stamp visible numbering onto sections and paragraphs."""
    default_child = min(parent_depth + 1, MAX_OUTLINE_DEPTH)
    title, level = _section_title_and_level(section, parent_depth, default_child)
    _bump_counters(counters, level)
    section_number = _format_section_number(counters, level)
    section_id = _section_id_from_number(section_number)
    section["id"] = section_id
    section["data-section-number"] = section_number

    heading_tag = _direct_heading_tag(section)
    if heading_tag and title:
        heading_tag.string = _prefix_text_once(heading_tag.get_text(" ", strip=True), section_number)

    for idx, p in enumerate(_direct_paragraph_tags(section), start=1):
        paragraph_number = f"{section_number}.{idx}"
        paragraph_id = _paragraph_id_from_section(section_id, idx)
        p["id"] = paragraph_id
        p["data-paragraph-number"] = paragraph_number
        p.string = _prefix_text_once(p.get_text(" ", strip=True), paragraph_number)

    for child in [c for c in _direct_child_tags(section) if c.name == "section"]:
        _annotate_section_tree_for_display(child, counters, parent_depth=level)

def annotate_html_with_numbering(html: str) -> str:
    """Public helper for creating human-visible heading and paragraph numbers."""
    soup = BeautifulSoup(html, "html.parser")
    root = find_book_root(soup)
    top_sections = [c for c in _direct_child_tags(root) if c.name == "section"]
    counters = [0] * MAX_OUTLINE_DEPTH
    if top_sections:
        for sec in top_sections:
            _annotate_section_tree_for_display(sec, counters, parent_depth=0)
    return str(soup)

"""
HTML parsing for section structure and legacy section-level chunking.

This module supports two HTML shapes:
- Format A: nested <section> trees
- Format B: flat h1/h2/h3 headings with sibling body blocks

The public parser returns SectionRecord objects so older callers remain stable.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from bs4 import BeautifulSoup, Tag

from .constants import MAX_OUTLINE_DEPTH
from .helpers import (
    _bump_counters,
    _collect_body_until_next_heading,
    _direct_child_tags,
    _format_section_number,
    _heading_level,
    _is_skippable_h1,
    find_book_root,
)
from .models import SectionRecord

def _is_nested_section_format(soup: BeautifulSoup) -> bool:
    """Detect nested-section HTML by looking for multiple outline-level sections."""
    root = find_book_root(soup)
    sections_with_level = [c for c in root.find_all("section") if c.get("data-outline-level") is not None]
    return len(sections_with_level) >= 2

def _section_title_heading_A(section: Tag) -> Optional[Tag]:
    """Find the first heading that acts as the title for a nested section."""
    for child in _direct_child_tags(section):
        if child.name == "section":
            continue
        if child.name in tuple(f"h{i}" for i in range(1, 7)) and child.get_text(strip=True):
            return child
        for h in child.find_all(tuple(f"h{i}" for i in range(1, 7))):
            if h.find_parent("section") is section and h.get_text(strip=True):
                return h
    return None

def _section_title_and_level_A(tag: Tag, parent_depth: int, default_child_level: int) -> Tuple[str, int]:
    """Resolve the section title and outline level for nested-section HTML."""
    attr_raw = tag.get("data-outline-level")
    attr_level = None
    if attr_raw is not None:
        try:
            attr_level = int(str(attr_raw).strip())
        except ValueError:
            pass

    h_title, h_level = None, None
    title_heading = _section_title_heading_A(tag)
    if title_heading is not None:
        h_title = title_heading.get_text(separator=" ", strip=True)
        h_level = int(title_heading.name[1])

    title = h_title or tag.get("aria-label") or ""
    title = re.sub(r"\s+", " ", title).strip()
    level = attr_level if attr_level is not None else (h_level if h_level else default_child_level)
    level = max(level, parent_depth + 1)
    return title, min(level, MAX_OUTLINE_DEPTH)

def _strip_nested_sections(tag: Tag) -> str:
    """Remove nested section nodes and return plain text from the remaining HTML."""
    clone = BeautifulSoup(str(tag), "html.parser")
    root = clone.find() or clone
    for nested in root.find_all("section"):
        nested.decompose()
    return root.get_text(separator="\n", strip=True)

def _parse_section_tree_A(section: Tag, counters: List[int], parent_depth: int) -> List[SectionRecord]:
    """Recursively flatten nested <section> HTML into SectionRecord objects."""
    default_child = min(parent_depth + 1, MAX_OUTLINE_DEPTH)
    title, level = _section_title_and_level_A(section, parent_depth, default_child)
    _bump_counters(counters, level)
    number = _format_section_number(counters, level)

    intro_tags = [c for c in _direct_child_tags(section) if c.name != "section"]
    child_sects = [c for c in _direct_child_tags(section) if c.name == "section"]

    if intro_tags:
        body = re.sub(r"\n{3,}", "\n\n", BeautifulSoup("".join(str(t) for t in intro_tags), "html.parser").get_text(separator="\n", strip=True)).strip()
    else:
        body = re.sub(r"\n{3,}", "\n\n", _strip_nested_sections(section)).strip()

    out: List[SectionRecord] = []
    if body:
        out.append(SectionRecord(section_number=number, title=title, body=body, level=level))
    for child in child_sects:
        out.extend(_parse_section_tree_A(child, counters, level))
    return out

def _parse_book_html_format_A(soup: BeautifulSoup) -> List[SectionRecord]:
    """Parse nested-section HTML into legacy SectionRecord objects."""
    root = find_book_root(soup)
    top_sections = [c for c in _direct_child_tags(root) if c.name == "section"]
    counters = [0] * MAX_OUTLINE_DEPTH
    records: List[SectionRecord] = []
    for sec in top_sections:
        records.extend(_parse_section_tree_A(sec, counters, parent_depth=0))
    return records

def _parse_book_html_format_B(soup: BeautifulSoup) -> List[SectionRecord]:
    """Parse flat heading HTML into legacy SectionRecord objects."""
    root = find_book_root(soup)
    all_headings = [
        tag for tag in root.find_all(["h1", "h2", "h3"])
        if not (tag.name == "h1" and _is_skippable_h1(tag))
        and tag.get_text(strip=True)
    ]
    counters: List[int] = [0] * MAX_OUTLINE_DEPTH
    records: List[SectionRecord] = []
    for heading in all_headings:
        level = int(heading.name[1])
        title = heading.get_text(separator=" ", strip=True)
        heading_id = heading.get("id", "")
        stop_levels = tuple(range(1, level + 1))
        body = _collect_body_until_next_heading(heading, stop_levels)
        if not body:
            continue
        _bump_counters(counters, level)
        number = _format_section_number(counters, level)
        records.append(SectionRecord(section_number=number, title=title, body=body, level=level, heading_id=heading_id))
    return records

def parse_book_html(html: str) -> List[SectionRecord]:
    """Public legacy parser that chooses the appropriate HTML shape automatically."""
    soup = BeautifulSoup(html, "html.parser")
    if _is_nested_section_format(soup):
        return _parse_book_html_format_A(soup)
    return _parse_book_html_format_B(soup)

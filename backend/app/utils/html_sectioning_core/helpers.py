"""
Low-level helpers shared by the parsing and annotation modules.

These functions centralize DOM traversal, whitespace cleanup, numbering
counters, and heading filtering so the higher-level modules can stay focused on
their own jobs.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional, Tuple

from bs4 import BeautifulSoup, NavigableString, Tag

from .constants import HEADING_TAGS, MAX_OUTLINE_DEPTH, _SKIP_H1_IDS, _SKIP_H1_TEXT_RE

def load_html_file(path: Path | str) -> str:
    """Load an HTML file from disk for parsing and RAG chunking."""
    p = Path(path)
    assert p.is_file(), f"HTML book not found at {p.resolve()}"
    return p.read_text(encoding="utf-8", errors="replace")

def find_book_root(soup: BeautifulSoup) -> Tag:
    """Find the most likely book root container, falling back to <body>."""
    for sel in ("article#climate-academy-book", "article.book", "main", "body"):
        found = soup.select_one(sel)
        if found:
            return found
    return soup

def _direct_child_tags(tag: Tag) -> List[Tag]:
    """Return only direct child tags, excluding text nodes and nested content."""
    return [c for c in tag.children if isinstance(c, Tag)]

def _normalize_whitespace(text: str) -> str:
    """Normalize spaces/newlines so paragraph text is stable and comparable."""
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()

def _bump_counters(counters: List[int], level: int) -> None:
    """Increment the current outline counter and reset deeper levels."""
    counters[level - 1] += 1
    for j in range(level, MAX_OUTLINE_DEPTH):
        counters[j] = 0

def _format_section_number(counters: List[int], level: int) -> str:
    """Format the active counters into a dotted section number."""
    return ".".join(str(counters[i]) for i in range(level))

def _heading_level(tag: Tag) -> Optional[int]:
    """Return heading level for h1..h6 tags, otherwise None."""
    if tag.name in HEADING_TAGS:
        return int(tag.name[1])
    return None

def _is_skippable_h1(tag: Tag) -> bool:
    """Ignore decorative or boilerplate h1 tags that are not real content."""
    tag_id = tag.get("id", "")
    tag_text = tag.get_text(strip=True)
    if tag_id in _SKIP_H1_IDS:
        return True
    if _SKIP_H1_TEXT_RE.search(tag_text):
        return True
    if not tag_text and tag.find("img"):
        return True
    return False

def _collect_body_until_next_heading(start_tag: Tag, stop_levels: Tuple[int, ...]) -> str:
    """Collect plain text between one heading and the next heading boundary."""
    parts: List[str] = []
    node = start_tag.next_sibling
    while node is not None:
        if isinstance(node, Tag):
            lvl = _heading_level(node)
            if lvl is not None and lvl in stop_levels:
                break
            if node.name == "section" and "footnotes" in node.get("class", []):
                break
            text = node.get_text(separator="\n", strip=True)
            if text:
                parts.append(text)
        elif isinstance(node, NavigableString):
            t = str(node).strip()
            if t:
                parts.append(t)
        node = node.next_sibling
    return _normalize_whitespace("\n".join(parts))

def _collect_paragraph_tags_until_next_heading(start_tag: Tag, stop_levels: Tuple[int, ...]) -> List[Tag]:
    """
    Return the raw block tags that belong to a section body.

    Future work: if the HTML layout becomes more irregular, this can be made
    more selective about which tags count as a paragraph-like block.
    """
    tags: List[Tag] = []
    node = start_tag.next_sibling
    while node is not None:
        if isinstance(node, Tag):
            lvl = _heading_level(node)
            if lvl is not None and lvl in stop_levels:
                break
            if node.name == "section" and "footnotes" in node.get("class", []):
                break
            tags.append(node)
        node = node.next_sibling
    return tags

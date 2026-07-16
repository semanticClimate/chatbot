"""
HTML annotation helpers for exact paragraph highlighting.

This module stamps section numbers, paragraph anchors, and wrapper elements on
the book HTML so the iframe viewer can jump to and highlight the exact target.
"""

from __future__ import annotations

from typing import List, Tuple

from bs4 import BeautifulSoup, Tag

from .constants import MAX_OUTLINE_DEPTH
from .helpers import (
    _bump_counters,
    _collect_body_until_next_heading,
    _direct_child_tags,
    _format_section_number,
    _heading_level,
    _is_skippable_h1,
    _normalize_whitespace,
    find_book_root,
)

def _section_title_heading_A(section: Tag):
    """Return the title heading inside a nested <section>."""
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
    """Resolve the title and outline level for nested-section HTML."""
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
    title = _normalize_whitespace(title)
    level = attr_level if attr_level is not None else (h_level if h_level else default_child_level)
    level = max(level, parent_depth + 1)
    return title, min(level, MAX_OUTLINE_DEPTH)

def _strip_nested_sections(tag: Tag) -> str:
    """Remove nested section nodes and return the remaining plain text."""
    clone = BeautifulSoup(str(tag), "html.parser")
    root = clone.find() or clone
    for nested in root.find_all("section"):
        nested.decompose()
    return root.get_text(separator="\n", strip=True)

def _annotate_format_A(soup: BeautifulSoup) -> str:
    """Annotate nested-section HTML with section and paragraph ids."""
    root = find_book_root(soup)
    top_sections = [c for c in _direct_child_tags(root) if c.name == "section"]
    counters = [0] * MAX_OUTLINE_DEPTH

    def _annotate_tree(section: Tag, parent_depth: int) -> None:
        default_child = min(parent_depth + 1, MAX_OUTLINE_DEPTH)
        _, level = _section_title_and_level_A(section, parent_depth, default_child)
        _bump_counters(counters, level)
        number = _format_section_number(counters, level)
        section["data-section-number"] = number
        section["id"] = f"section-{number.replace('.', '-')}"
        title_heading = _section_title_heading_A(section)
        if title_heading is not None:
            title_heading["data-section-number"] = number

        p_idx = 0
        for child in _direct_child_tags(section):
            if child.name == "p":
                para_n = p_idx + 1
                child["id"] = f"para-{number}-{para_n}"
                child["data-para-index"] = str(p_idx)
                child["data-paragraph-number"] = f"{number}.{para_n}"
                p_idx += 1
            if child.name == "section":
                _annotate_tree(child, parent_depth=level)

    for sec in top_sections:
        _annotate_tree(sec, parent_depth=0)
    return str(soup)

def _annotate_format_B_para(soup: BeautifulSoup) -> str:
    """
    Annotate flat-heading HTML with section ids, paragraph ids, and wrapper divs.

    Limitation: body blocks are detected from sibling blocks after each heading
    until the next same-or-higher heading.
    """
    root = find_book_root(soup)
    all_headings = [
        tag for tag in root.find_all(["h1", "h2", "h3"])
        if not (tag.name == "h1" and _is_skippable_h1(tag))
        and tag.get_text(strip=True)
    ]

    counters: List[int] = [0] * MAX_OUTLINE_DEPTH
    heading_meta: dict[int, Tuple[str, int]] = {}

    for heading in all_headings:
        level = int(heading.name[1])
        stop_levels = tuple(range(1, level + 1))
        body = _collect_body_until_next_heading(heading, stop_levels)
        if not body:
            continue

        _bump_counters(counters, level)
        number = _format_section_number(counters, level)

        heading["data-section-number"] = number
        orig_id = heading.get("id", "")
        if orig_id:
            heading["data-original-id"] = orig_id
        heading["id"] = f"section-{number.replace('.', '-')}"
        heading_meta[id(heading)] = (number, level)

        para_idx = 0
        node = heading.next_sibling
        while node is not None:
            if isinstance(node, Tag):
                lvl = _heading_level(node)
                if lvl is not None and lvl in stop_levels:
                    break
                if node.name == "section" and "footnotes" in node.get("class", []):
                    break
                text = node.get_text(strip=True)
                if text and node.name in ("p", "ul", "ol", "table", "blockquote", "figure", "div"):
                    para_n = para_idx + 1
                    node["id"] = f"para-{number}-{para_n}"
                    node["data-para-index"] = str(para_idx)
                    node["data-section-num"] = number
                    node["data-paragraph-number"] = f"{number}.{para_n}"
                    para_idx += 1
            node = node.next_sibling

    stamped_headings: set[int] = set(heading_meta.keys())

    for heading in reversed(all_headings):
        if id(heading) not in heading_meta:
            continue

        number, level = heading_meta[id(heading)]
        stop_levels_set = set(range(1, level + 1))

        siblings_to_wrap: List = []
        node = heading.next_sibling
        while node is not None:
            next_node = node.next_sibling
            if isinstance(node, Tag):
                lvl = _heading_level(node)
                if lvl is not None and lvl in stop_levels_set:
                    break
                if id(node) in stamped_headings:
                    break
                if "ca-section" in node.get("class", []):
                    break
                if node.name == "section" and "footnotes" in node.get("class", []):
                    break
            siblings_to_wrap.append(node)
            node = next_node

        wrapper = soup.new_tag(
            "div",
            **{
                "class": "ca-section",
                "data-section-number": number,
                "data-section-level": str(level),
            },
        )
        heading.insert_before(wrapper)
        wrapper.append(heading.extract())
        for sib in siblings_to_wrap:
            wrapper.append(sib.extract())

    return str(soup)

def annotate_html_with_section_ids(html: str) -> str:
    """Public entry point for highlight anchors used by the iframe viewer."""
    soup = BeautifulSoup(html, "html.parser")
    # Use the same nested-section heuristic as the parser.
    root = find_book_root(soup)
    sections_with_level = [c for c in root.find_all("section") if c.get("data-outline-level") is not None]
    if len(sections_with_level) >= 2:
        return _annotate_format_A(soup)
    return _annotate_format_B_para(soup)

"""
HTML book outline parsing, decimal section numbering, and chunking for RAG.

Expects structured HTML (see docs/HTML_SECTION_NESTING.md): nested <section>
elements with data-outline-level (recommended) and a heading (h1–h6) per section.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from bs4 import BeautifulSoup, NavigableString, Tag

HEADING_TAGS = tuple(f"h{i}" for i in range(1, 7))
MAX_OUTLINE_DEPTH = 6


@dataclass(frozen=True)
class SectionRecord:
    """One indexed section with extractable body text (no nested <section> content)."""

    section_number: str
    title: str
    body: str
    level: int


def load_html_file(path: Path | str) -> str:
    p = Path(path)
    assert p.is_file(), f"HTML book not found at {p.resolve()}"
    return p.read_text(encoding="utf-8", errors="replace")


def find_book_root(soup: BeautifulSoup) -> Tag:
    """Prefer <article id='climate-academy-book'>; fall back to <main> or <body>."""
    for sel in ("article#climate-academy-book", "article.book", "main", "body"):
        found = soup.select_one(sel)
        if found:
            return found
    return soup


def _direct_child_tags(tag: Tag) -> List[Tag]:
    return [c for c in tag.children if isinstance(c, Tag)]


def _section_level_from_attr(tag: Tag) -> Optional[int]:
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


def _first_heading_title(tag: Tag) -> Tuple[Optional[str], Optional[int]]:
    """First h1–h6 in document order within this subtree; returns (title, level 1–6)."""
    for h in tag.find_all(HEADING_TAGS):
        text = h.get_text(separator=" ", strip=True)
        if not text:
            continue
        level = int(h.name[1])
        return text, level
    return None, None


def _heading_from_direct_content(section: Tag) -> Tuple[Optional[str], Optional[int]]:
    """
    Heading that belongs to this section only — not inside nested <section> children.
    """
    for child in _direct_child_tags(section):
        if child.name == "section":
            continue
        if child.name in HEADING_TAGS:
            text = child.get_text(separator=" ", strip=True)
            if text:
                return text, int(child.name[1])
        for h in child.find_all(HEADING_TAGS):
            parent_sec = h.find_parent("section")
            if parent_sec is section and h.get_text(strip=True):
                return h.get_text(separator=" ", strip=True), int(h.name[1])
    return None, None


def _section_title_and_level(tag: Tag, parent_depth: int, default_child_level: int) -> Tuple[str, int]:
    """
    Title from first heading in section. Level from data-outline-level, else heading level,
    else default_child_level (typically parent_depth + 1).
    """
    attr_level = _section_level_from_attr(tag)
    h_title, h_level = _heading_from_direct_content(tag)
    title = h_title or tag.get("aria-label") or ""
    title = re.sub(r"\s+", " ", title).strip()
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


def _split_intro_and_child_sections(section: Tag) -> Tuple[List[Tag], List[Tag]]:
    intro: List[Tag] = []
    children: List[Tag] = []
    for child in _direct_child_tags(section):
        if child.name == "section":
            children.append(child)
        else:
            intro.append(child)
    return intro, children


def _strip_nested_sections(tag: Tag) -> str:
    """Text content of tag with nested <section> subtrees removed (avoid double-counting)."""
    clone = BeautifulSoup(str(tag), "html.parser")
    root = clone.find() or clone
    for nested in root.find_all("section"):
        nested.decompose()
    return root.get_text(separator="\n", strip=True)


def _normalize_whitespace(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def _bump_counters(counters: List[int], level: int) -> None:
    """1-based level; increment at depth and zero deeper slots."""
    idx = level - 1
    counters[idx] += 1
    for j in range(level, MAX_OUTLINE_DEPTH):
        counters[j] = 0


def _format_section_number(counters: List[int], level: int) -> str:
    return ".".join(str(counters[i]) for i in range(level))


def _parse_section_tree(section: Tag, counters: List[int], parent_depth: int) -> List[SectionRecord]:
    default_child = min(parent_depth + 1, MAX_OUTLINE_DEPTH)
    title, level = _section_title_and_level(section, parent_depth, default_child)
    _bump_counters(counters, level)
    number = _format_section_number(counters, level)

    intro_tags, child_sections = _split_intro_and_child_sections(section)
    if intro_tags:
        container = section
        body = _normalize_whitespace(
            BeautifulSoup("".join(str(t) for t in intro_tags), "html.parser").get_text(
                separator="\n", strip=True
            )
        )
    else:
        body = ""

    if not body:
        body = _normalize_whitespace(_strip_nested_sections(section))
        for nested in section.find_all("section"):
            nested_body = nested.get_text(separator="\n", strip=True)
            if nested_body and nested_body in body:
                body = body.replace(nested_body, "")
        body = _normalize_whitespace(body)

    out: List[SectionRecord] = []
    if body:
        out.append(
            SectionRecord(section_number=number, title=title, body=body, level=level)
        )

    child_parent_depth = level
    for child in child_sections:
        out.extend(_parse_section_tree(child, counters, child_parent_depth))
    return out


def parse_book_html(html: str) -> List[SectionRecord]:
    """
    Parse book HTML into section records with decimal section_number strings.

    Root: first match of article#climate-academy-book, article.book, main, or body.
    Only direct <section> children of the root are outline roots; if none, one synthetic
    section "1" is created from visible text (nested sections stripped).
    """
    soup = BeautifulSoup(html, "html.parser")
    root = find_book_root(soup)
    top_sections = [c for c in _direct_child_tags(root) if c.name == "section"]
    counters = [0] * MAX_OUTLINE_DEPTH
    records: List[SectionRecord] = []

    if top_sections:
        for sec in top_sections:
            records.extend(_parse_section_tree(sec, counters, parent_depth=0))
        return records

    title, _ = _first_heading_title(root)
    if not title:
        t = root.find(["h1", "h2"])
        title = t.get_text(strip=True) if t else "Book"
    body = _normalize_whitespace(_strip_nested_sections(root))
    if not body:
        body = _normalize_whitespace(root.get_text(separator="\n", strip=True))
    if body:
        counters[0] = 1
        records.append(
            SectionRecord(section_number="1", title=title, body=body, level=1)
        )
    return records


def word_chunks(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Split on words; chunk_size and overlap are word counts."""
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


@dataclass(frozen=True)
class IndexedChunk:
    """One embedding unit with section metadata."""

    document: str
    section_number: str
    section_title: str
    chunk_index: int


def records_to_indexed_chunks(
    records: Iterable[SectionRecord],
    chunk_size: int,
    chunk_overlap: int,
) -> List[IndexedChunk]:
    out: List[IndexedChunk] = []
    for rec in records:
        for idx, part in enumerate(word_chunks(rec.body, chunk_size, chunk_overlap)):
            header = f"[§ {rec.section_number}"
            if rec.title:
                header += f" — {rec.title}"
            header += "]"
            doc = f"{header}\n{part}"
            out.append(
                IndexedChunk(
                    document=doc,
                    section_number=rec.section_number,
                    section_title=rec.title,
                    chunk_index=idx,
                )
            )
    return out


def format_passage_for_prompt(section_number: str, section_title: str, body: str) -> str:
    """Format a retrieved chunk for the LLM (strip duplicate bracket line if present)."""
    t = body.strip()
    if t.startswith("[§"):
        return t
    line = f"[§ {section_number}"
    if section_title:
        line += f" — {section_title}"
    line += "]"
    return f"{line}\n{t}"


def parse_html_path_to_chunks(
    path: Path | str,
    chunk_size: int,
    chunk_overlap: int,
) -> List[IndexedChunk]:
    html = load_html_file(path)
    records = parse_book_html(html)
    return records_to_indexed_chunks(records, chunk_size, chunk_overlap)

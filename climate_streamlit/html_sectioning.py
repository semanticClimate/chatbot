"""
html_sectioning.py  —  Climate Academy RAG · Paragraph-Level Chunking
======================================================================
KEY UPGRADE over the previous version:
  • Every PARAGRAPH is its own chunk (not word-window chunks of a whole section).
  • Each chunk gets a unique chunk_id  →  "p-{section_number}-{para_index}"
  • Each chunk gets a unique anchor_id →  "para-{section_number}-{para_index}"
  • These anchor IDs are written into the annotated HTML so the viewer can
    scroll to and highlight EXACTLY that paragraph, not the whole section.

Public API (unchanged call-sites in app.py):
  annotate_html_with_section_ids(html: str) → str
  parse_html_path_to_chunks(path, chunk_size, chunk_overlap) → List[IndexedChunk]
  format_passage_for_prompt(section_number, section_title, body) → str
  parse_book_html(html) → List[SectionRecord]          (unchanged, kept for tests)

New:
  parse_html_to_paragraph_chunks(path) → List[ParagraphChunk]
    Returns one chunk per paragraph, each with chunk_id + anchor_id.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from bs4 import BeautifulSoup, NavigableString, Tag

# ── constants ─────────────────────────────────────────────────────────────────
HEADING_TAGS      = tuple(f"h{i}" for i in range(1, 7))
MAX_OUTLINE_DEPTH = 6

_SKIP_H1_IDS = {"section", "contents", "section-3", "section-4", "section-5"}
_SKIP_H1_TEXT_RE = re.compile(
    r"^\s*$|description automatically generated|logo with text", re.I
)

# Minimum meaningful paragraph length (characters). Shorter paragraphs are
# merged with the previous one so we don't create empty/trivial chunks.
MIN_PARA_CHARS = 40


# ── data structures ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class SectionRecord:
    """One section of the book (heading + body text). Used by legacy API."""
    section_number: str
    title:          str
    body:           str
    level:          int
    heading_id:     str = ""


@dataclass(frozen=True)
class ParagraphChunk:
    """
    One paragraph = one RAG chunk.

    chunk_id  :  unique stable string  →  stored in ChromaDB metadata
    anchor_id :  HTML element id       →  used by viewer to highlight EXACTLY this ¶
    """
    chunk_id:       str    # e.g. "p-3.2-0"
    anchor_id:      str    # e.g. "para-3.2-0"
    document:       str    # text sent to the LLM (includes section header)
    section_number: str
    section_title:  str
    para_index:     int    # 0-based index within the section
    heading_id:     str = ""


# kept for backward-compat (app.py imports this name)
@dataclass(frozen=True)
class IndexedChunk:
    document:       str
    section_number: str
    section_title:  str
    chunk_index:    int
    heading_id:     str = ""
    chunk_id:       str = ""
    anchor_id:      str = ""


# ── shared utilities ──────────────────────────────────────────────────────────

def load_html_file(path: Path | str) -> str:
    p = Path(path)
    assert p.is_file(), f"HTML book not found at {p.resolve()}"
    return p.read_text(encoding="utf-8", errors="replace")


def find_book_root(soup: BeautifulSoup) -> Tag:
    for sel in ("article#climate-academy-book", "article.book", "main", "body"):
        found = soup.select_one(sel)
        if found:
            return found
    return soup


def _direct_child_tags(tag: Tag) -> List[Tag]:
    return [c for c in tag.children if isinstance(c, Tag)]


def _normalize_whitespace(text: str) -> str:
    text = text.replace("\u00a0", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def _bump_counters(counters: List[int], level: int) -> None:
    counters[level - 1] += 1
    for j in range(level, MAX_OUTLINE_DEPTH):
        counters[j] = 0


def _format_section_number(counters: List[int], level: int) -> str:
    return ".".join(str(counters[i]) for i in range(level))


# ── format detection ──────────────────────────────────────────────────────────

def _is_nested_section_format(soup: BeautifulSoup) -> bool:
    root = find_book_root(soup)
    sections_with_level = [
        c for c in root.find_all("section")
        if c.get("data-outline-level") is not None
    ]
    return len(sections_with_level) >= 2


def _heading_level(tag: Tag) -> Optional[int]:
    if tag.name in HEADING_TAGS:
        return int(tag.name[1])
    return None


def _is_skippable_h1(tag: Tag) -> bool:
    tag_id   = tag.get("id", "")
    tag_text = tag.get_text(strip=True)
    if tag_id in _SKIP_H1_IDS:
        return True
    if _SKIP_H1_TEXT_RE.search(tag_text):
        return True
    if not tag_text and tag.find("img"):
        return True
    return False


def _collect_body_until_next_heading(
    start_tag: Tag, stop_levels: Tuple[int, ...]
) -> str:
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


def _collect_paragraph_tags_until_next_heading(
    start_tag: Tag, stop_levels: Tuple[int, ...]
) -> List[Tag]:
    """
    Returns the actual Tag objects (p, ul, ol, table, blockquote …) that form
    the body of a section — stopping before the next heading at stop_levels.
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


# ── FORMAT B parsing (flat h1/h2/h3 headings) ────────────────────────────────

def _parse_book_html_format_B(soup: BeautifulSoup) -> List[SectionRecord]:
    root = find_book_root(soup)
    all_headings = [
        tag for tag in root.find_all(["h1", "h2", "h3"])
        if not (tag.name == "h1" and _is_skippable_h1(tag))
        and tag.get_text(strip=True)
    ]
    counters: List[int] = [0] * MAX_OUTLINE_DEPTH
    records:  List[SectionRecord] = []
    for heading in all_headings:
        level       = int(heading.name[1])
        title       = heading.get_text(separator=" ", strip=True)
        heading_id  = heading.get("id", "")
        stop_levels = tuple(range(1, level + 1))
        body        = _collect_body_until_next_heading(heading, stop_levels)
        if not body:
            continue
        _bump_counters(counters, level)
        number = _format_section_number(counters, level)
        records.append(SectionRecord(
            section_number=number,
            title=title,
            body=body,
            level=level,
            heading_id=heading_id,
        ))
    return records


# ── FORMAT A parsing (nested <section> elements) ──────────────────────────────

def _section_title_and_level_A(
    tag: Tag, parent_depth: int, default_child_level: int
) -> Tuple[str, int]:
    attr_raw = tag.get("data-outline-level")
    attr_level = None
    if attr_raw is not None:
        try:
            attr_level = int(str(attr_raw).strip())
        except ValueError:
            pass

    h_title, h_level = None, None
    for child in _direct_child_tags(tag):
        if child.name == "section":
            continue
        if child.name in HEADING_TAGS:
            txt = child.get_text(separator=" ", strip=True)
            if txt:
                h_title, h_level = txt, int(child.name[1])
                break
        for h in child.find_all(HEADING_TAGS):
            parent_sec = h.find_parent("section")
            if parent_sec is tag and h.get_text(strip=True):
                h_title = h.get_text(separator=" ", strip=True)
                h_level = int(h.name[1])
                break
        if h_title:
            break

    title  = h_title or tag.get("aria-label") or ""
    title  = re.sub(r"\s+", " ", title).strip()
    level  = attr_level if attr_level is not None else (h_level if h_level else default_child_level)
    level  = max(level, parent_depth + 1)
    return title, min(level, MAX_OUTLINE_DEPTH)


def _strip_nested_sections(tag: Tag) -> str:
    clone = BeautifulSoup(str(tag), "html.parser")
    root  = clone.find() or clone
    for nested in root.find_all("section"):
        nested.decompose()
    return root.get_text(separator="\n", strip=True)


def _parse_section_tree_A(
    section: Tag, counters: List[int], parent_depth: int
) -> List[SectionRecord]:
    default_child = min(parent_depth + 1, MAX_OUTLINE_DEPTH)
    title, level  = _section_title_and_level_A(section, parent_depth, default_child)
    _bump_counters(counters, level)
    number = _format_section_number(counters, level)

    intro_tags  = [c for c in _direct_child_tags(section) if c.name != "section"]
    child_sects = [c for c in _direct_child_tags(section) if c.name == "section"]

    if intro_tags:
        body = _normalize_whitespace(
            BeautifulSoup("".join(str(t) for t in intro_tags), "html.parser")
            .get_text(separator="\n", strip=True)
        )
    else:
        body = _normalize_whitespace(_strip_nested_sections(section))

    out: List[SectionRecord] = []
    if body:
        out.append(SectionRecord(section_number=number, title=title,
                                  body=body, level=level))
    for child in child_sects:
        out.extend(_parse_section_tree_A(child, counters, level))
    return out


def _parse_book_html_format_A(soup: BeautifulSoup) -> List[SectionRecord]:
    root         = find_book_root(soup)
    top_sections = [c for c in _direct_child_tags(root) if c.name == "section"]
    counters     = [0] * MAX_OUTLINE_DEPTH
    records: List[SectionRecord] = []
    for sec in top_sections:
        records.extend(_parse_section_tree_A(sec, counters, parent_depth=0))
    return records


# ── PUBLIC: parse_book_html ───────────────────────────────────────────────────

def parse_book_html(html: str) -> List[SectionRecord]:
    soup = BeautifulSoup(html, "html.parser")
    if _is_nested_section_format(soup):
        return _parse_book_html_format_A(soup)
    return _parse_book_html_format_B(soup)


# ── NEW: Paragraph-level chunking ─────────────────────────────────────────────

def _split_body_into_paragraphs(body_text: str) -> List[str]:
    """
    Split a section body into individual paragraphs.
    Works on the plain-text representation; double newlines = paragraph break.
    Short fragments (<MIN_PARA_CHARS) are merged into the previous paragraph.
    """
    raw_paras = re.split(r"\n{2,}", body_text)
    paras: List[str] = []
    for raw in raw_paras:
        text = _normalize_whitespace(raw)
        if not text:
            continue
        if paras and len(text) < MIN_PARA_CHARS:
            paras[-1] = paras[-1] + " " + text
        else:
            paras.append(text)
    return paras


def _collect_paragraph_texts_for_section(
    heading_tag: Tag, stop_levels: Tuple[int, ...]
) -> List[str]:
    """
    Collect the text of individual block-level children (p, li-groups, etc.)
    for a section. Returns one string per paragraph-like block.
    """
    para_texts: List[str] = []
    current_list: List[str] = []   # accumulate consecutive list items

    def flush_list() -> None:
        if current_list:
            merged = " ".join(current_list)
            if para_texts and len(merged) < MIN_PARA_CHARS:
                para_texts[-1] = para_texts[-1] + " " + merged
            else:
                para_texts.append(merged)
            current_list.clear()

    node = heading_tag.next_sibling
    while node is not None:
        if isinstance(node, Tag):
            lvl = _heading_level(node)
            if lvl is not None and lvl in stop_levels:
                break
            if node.name == "section" and "footnotes" in node.get("class", []):
                break

            if node.name in ("ul", "ol"):
                # flatten list into one paragraph
                flush_list()
                items = [li.get_text(separator=" ", strip=True)
                         for li in node.find_all("li") if li.get_text(strip=True)]
                combined = "; ".join(items)
                if combined:
                    para_texts.append(combined)
            elif node.name == "p":
                flush_list()
                text = node.get_text(separator=" ", strip=True)
                if text:
                    if para_texts and len(text) < MIN_PARA_CHARS:
                        para_texts[-1] = para_texts[-1] + " " + text
                    else:
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
    return [_normalize_whitespace(p) for p in para_texts if p.strip()]


def _section_paragraphs_from_format_B(soup: BeautifulSoup) -> List[Tuple[str, str, str, List[str]]]:
    """
    Returns list of (section_number, section_title, heading_id, [para_texts])
    """
    root = find_book_root(soup)
    all_headings = [
        tag for tag in root.find_all(["h1", "h2", "h3"])
        if not (tag.name == "h1" and _is_skippable_h1(tag))
        and tag.get_text(strip=True)
    ]
    counters: List[int] = [0] * MAX_OUTLINE_DEPTH
    results = []
    for heading in all_headings:
        level       = int(heading.name[1])
        title       = heading.get_text(separator=" ", strip=True)
        heading_id  = heading.get("id", "")
        stop_levels = tuple(range(1, level + 1))
        paras       = _collect_paragraph_texts_for_section(heading, stop_levels)
        if not paras:
            continue
        _bump_counters(counters, level)
        number = _format_section_number(counters, level)
        results.append((number, title, heading_id, paras))
    return results


def parse_html_to_paragraph_chunks(path: Path | str) -> List[ParagraphChunk]:
    """
    Parse the book HTML and return ONE ParagraphChunk per paragraph.
    This is the main entry point for the new RAG pipeline.
    """
    html  = load_html_file(path)
    soup  = BeautifulSoup(html, "html.parser")
    chunks: List[ParagraphChunk] = []

    if _is_nested_section_format(soup):
        # For Format A: fall back to section-level → split by double newline
        records = _parse_book_html_format_A(soup)
        for rec in records:
            paras = _split_body_into_paragraphs(rec.body)
            for idx, para in enumerate(paras):
                chunk_id  = f"p-{rec.section_number}-{idx}"
                anchor_id = f"para-{rec.section_number}-{idx}"
                header    = f"[§ {rec.section_number} — {rec.title}]"
                chunks.append(ParagraphChunk(
                    chunk_id       = chunk_id,
                    anchor_id      = anchor_id,
                    document       = f"{header}\n{para}",
                    section_number = rec.section_number,
                    section_title  = rec.title,
                    para_index     = idx,
                    heading_id     = rec.heading_id,
                ))
    else:
        # Format B — paragraph-aware collection
        sections = _section_paragraphs_from_format_B(soup)
        for (number, title, heading_id, paras) in sections:
            for idx, para in enumerate(paras):
                chunk_id  = f"p-{number}-{idx}"
                anchor_id = f"para-{number}-{idx}"
                header    = f"[§ {number} — {title}]"
                chunks.append(ParagraphChunk(
                    chunk_id       = chunk_id,
                    anchor_id      = anchor_id,
                    document       = f"{header}\n{para}",
                    section_number = number,
                    section_title  = title,
                    para_index     = idx,
                    heading_id     = heading_id,
                ))
    return chunks


# ── ANNOTATE HTML — injects anchor IDs per paragraph ─────────────────────────

def annotate_html_with_section_ids(html: str) -> str:
    """
    1. Assigns §-numbers to headings (same as before).
    2. NEW: Injects   id="para-{section}-{idx}"   on every paragraph element
       so the viewer can highlight EXACTLY that paragraph.
    3. Wraps each section in a ca-section div for fallback section-level highlighting.
    """
    soup = BeautifulSoup(html, "html.parser")
    if _is_nested_section_format(soup):
        return _annotate_format_A(soup)
    return _annotate_format_B_para(soup)


def _annotate_format_A(soup: BeautifulSoup) -> str:
    """Format A: annotate <section> elements (unchanged logic)."""
    root         = find_book_root(soup)
    top_sections = [c for c in _direct_child_tags(root) if c.name == "section"]
    counters     = [0] * MAX_OUTLINE_DEPTH

    def _annotate_tree(section: Tag, parent_depth: int) -> None:
        default_child = min(parent_depth + 1, MAX_OUTLINE_DEPTH)
        _, level      = _section_title_and_level_A(section, parent_depth, default_child)
        _bump_counters(counters, level)
        number = _format_section_number(counters, level)
        section["data-section-number"] = number
        section["id"] = f"section-{number.replace('.', '-')}"

        # Inject paragraph anchor IDs on <p> children
        p_idx = 0
        for child in _direct_child_tags(section):
            if child.name == "p":
                child["id"] = f"para-{number}-{p_idx}"
                child["data-para-index"] = str(p_idx)
                p_idx += 1
            if child.name == "section":
                _annotate_tree(child, parent_depth=level)

    for sec in top_sections:
        _annotate_tree(sec, parent_depth=0)

    return str(soup)


def _annotate_format_B_para(soup: BeautifulSoup) -> str:
    """
    Format B: flat HTML.
    1. Stamp §-numbers on headings (skip if no body, same as parser).
    2. Inject  id="para-{sec}-{idx}"  on each block-level body element.
    3. Wrap heading + body in <div class="ca-section"> for section-level highlight.
    """
    root = find_book_root(soup)

    all_headings = [
        tag for tag in root.find_all(["h1", "h2", "h3"])
        if not (tag.name == "h1" and _is_skippable_h1(tag))
        and tag.get_text(strip=True)
    ]

    counters: List[int] = [0] * MAX_OUTLINE_DEPTH
    heading_meta: dict[int, Tuple[str, int]] = {}

    # ── Pass 1: stamp headings and paragraph elements ─────────────────────────
    for heading in all_headings:
        level       = int(heading.name[1])
        stop_levels = tuple(range(1, level + 1))
        body        = _collect_body_until_next_heading(heading, stop_levels)
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

        # Stamp paragraph anchor IDs on body elements
        para_idx = 0
        node = heading.next_sibling
        while node is not None:
            if isinstance(node, Tag):
                lvl = _heading_level(node)
                if lvl is not None and lvl in stop_levels:
                    break
                if node.name == "section" and "footnotes" in node.get("class", []):
                    break
                # Stamp any block that has visible text
                text = node.get_text(strip=True)
                if text and node.name in ("p", "ul", "ol", "table",
                                          "blockquote", "figure", "div"):
                    node["id"]               = f"para-{number}-{para_idx}"
                    node["data-para-index"]  = str(para_idx)
                    node["data-section-num"] = number
                    para_idx += 1
            node = node.next_sibling

    stamped_headings: set[int] = set(heading_meta.keys())

    # ── Pass 2: wrap heading + body in ca-section div ─────────────────────────
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
                "class":               "ca-section",
                "data-section-number": number,
                "data-section-level":  str(level),
            }
        )
        heading.insert_before(wrapper)
        wrapper.append(heading.extract())
        for sib in siblings_to_wrap:
            wrapper.append(sib.extract())

    return str(soup)


# ── PUBLIC: legacy helpers (app.py imports these) ─────────────────────────────

def format_passage_for_prompt(
    section_number: str, section_title: str, body: str
) -> str:
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
    """
    Legacy entry point — returns IndexedChunk list.
    Now backed by paragraph-level chunking; chunk_size / chunk_overlap ignored
    (each paragraph IS one chunk already).
    """
    para_chunks = parse_html_to_paragraph_chunks(path)
    out: List[IndexedChunk] = []
    for i, pc in enumerate(para_chunks):
        out.append(IndexedChunk(
            document       = pc.document,
            section_number = pc.section_number,
            section_title  = pc.section_title,
            chunk_index    = pc.para_index,
            heading_id     = pc.heading_id,
            chunk_id       = pc.chunk_id,
            anchor_id      = pc.anchor_id,
        ))
    return out


# ── self-test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "input/full_student_book.html"
    chunks = parse_html_to_paragraph_chunks(path)
    print(f"Total paragraph chunks: {len(chunks)}")
    for c in chunks[:10]:
        print(f"  {c.chunk_id:25s}  anchor={c.anchor_id:25s}  §{c.section_number}  {c.section_title[:40]}")
        print(f"    {c.document[:100].replace(chr(10),' ')!r}")
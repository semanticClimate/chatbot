"""Annotate CABook HTML text nodes with encyclopedia links."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import List, Tuple, Union

from lxml import etree
from lxml import html as lxml_html

from encyclopedia.cabook_annotate.encyclopedia_index import TermIndex
from encyclopedia.cabook_annotate.link_normalizer import (
    inject_stylesheet,
    stylesheet_href_for_html,
)
from encyclopedia.cabook_annotate.phrase_matcher import find_non_overlapping_matches
from encyclopedia.config_loader import AnnotateSettings

Part = Union[str, etree._Element]


def _link_element(
    match_surface: str,
    href: str,
    entry_id: str,
    canonical_term: str,
    settings: AnnotateSettings,
) -> etree._Element:
    links = settings.links
    anchor = etree.Element("a")
    anchor.set("href", href)
    anchor.set("class", links.link_class)
    anchor.set(links.data_entry_id_attr, entry_id)
    anchor.set(links.data_canonical_term_attr, canonical_term)
    anchor.text = match_surface
    return anchor


def _parts_for_text(
    text: str,
    term_index: TermIndex,
    settings: AnnotateSettings,
    counts: Counter,
) -> List[Part]:
    matches = find_non_overlapping_matches(
        text,
        term_index.sorted_phrases,
        term_index.phrase_to_entry_id,
        ignore_case=settings.matching.ignore_case,
        min_term_length=settings.matching.min_term_length,
    )
    if not matches:
        return [text]

    parts: List[Part] = []
    cursor = 0
    for match in matches:
        if match.start > cursor:
            parts.append(text[cursor : match.start])
        entry = term_index.entries_by_id[match.entry_id]
        parts.append(
            _link_element(
                match.surface,
                entry.href,
                entry.wikidata_id,
                entry.canonical_term,
                settings,
            )
        )
        counts[match.entry_id] += 1
        cursor = match.end
    if cursor < len(text):
        parts.append(text[cursor:])
    return parts


def _apply_parts_to_text_attr(parent: etree._Element, parts: List[Part]) -> None:
    parent.text = None
    if not parts:
        return
    index = 0
    if isinstance(parts[0], str):
        parent.text = parts[0]
        index = 1
    last_elem = None
    for part in parts[index:]:
        if isinstance(part, str):
            if last_elem is not None:
                last_elem.tail = (last_elem.tail or "") + part
            else:
                parent.text = (parent.text or "") + part
        else:
            parent.append(part)
            last_elem = part


def _apply_parts_to_tail(parent: etree._Element, parts: List[Part]) -> None:
    parent.tail = None
    if not parts:
        return
    index = 0
    if isinstance(parts[0], str):
        parent.tail = parts[0]
        index = 1
    anchor = parent
    for part in parts[index:]:
        if isinstance(part, str):
            anchor.tail = (anchor.tail or "") + part
        else:
            anchor.addnext(part)
            anchor = part


def _walk_and_annotate(
    root: etree._Element,
    term_index: TermIndex,
    settings: AnnotateSettings,
    counts: Counter,
) -> None:
    skip = set(settings.matching.skip_tags)

    for elem in root.iter():
        tag = elem.tag.lower() if isinstance(elem.tag, str) else ""
        if tag in skip:
            continue
        if elem.text and elem.text.strip():
            parts = _parts_for_text(elem.text, term_index, settings, counts)
            if len(parts) > 1 or (parts and not isinstance(parts[0], str)):
                _apply_parts_to_text_attr(elem, parts)
            elif parts and isinstance(parts[0], str) and parts[0] != elem.text:
                elem.text = parts[0]
        for child in elem:
            if child.tail and child.tail.strip():
                parts = _parts_for_text(child.tail, term_index, settings, counts)
                if len(parts) > 1 or (parts and not isinstance(parts[0], str)):
                    _apply_parts_to_tail(child, parts)
                elif parts and isinstance(parts[0], str) and parts[0] != child.tail:
                    child.tail = parts[0]


def annotate_book_html(
    book_html_path: Path,
    output_path: Path,
    term_index: TermIndex,
    settings: AnnotateSettings,
) -> Tuple[int, Counter]:
    parser = lxml_html.HTMLParser(encoding="utf-8")
    tree = lxml_html.parse(str(book_html_path), parser)
    root = tree.getroot()
    counts: Counter = Counter()

    body = root.find(".//body")
    target = body if body is not None else root
    _walk_and_annotate(target, term_index, settings, counts)

    css_href = stylesheet_href_for_html(output_path, settings.paths.link_css)
    inject_stylesheet(root, css_href)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(
        str(output_path),
        encoding="utf-8",
        method="html",
        pretty_print=False,
    )
    return sum(counts.values()), counts

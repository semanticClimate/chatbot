"""Load encyclopedia entries and surface forms from AMI HTML."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set

from lxml import html as lxml_html

from encyclopedia.cabook_annotate.variant_expander import expand_surface_forms
from encyclopedia.config_loader import AnnotateSettings


@dataclass(frozen=True)
class EncyclopediaEntry:
    wikidata_id: str
    canonical_term: str
    fragment: str
    href: str
    surface_forms: frozenset


@dataclass
class TermIndex:
    entries_by_id: Dict[str, EncyclopediaEntry]
    phrase_to_entry_id: Dict[str, str]
    sorted_phrases: List[str]


def _clean_synonym(text: str, strip_suffix: str) -> str:
    cleaned = text.strip()
    if strip_suffix and cleaned.endswith(strip_suffix):
        cleaned = cleaned[: -len(strip_suffix)].strip()
    return cleaned


def _fragment_for_entry(wikidata_id: str, settings: AnnotateSettings) -> str:
    return settings.links.fragment_template.format(wikidata_id=wikidata_id)


def _href_for_entry(fragment: str, settings: AnnotateSettings) -> str:
    return settings.links.href_template.format(fragment=fragment)


def _collect_surface_forms(entry_elem, settings: AnnotateSettings) -> Set[str]:
    variant_settings = settings.variants
    forms: Set[str] = set()
    term_attr = (entry_elem.get("term") or "").strip()
    if term_attr:
        forms.add(term_attr)

    wiki_links = entry_elem.xpath(".//a[contains(@class, 'wikipedia-link')]")
    for link in wiki_links:
        label = (link.text_content() or "").strip()
        if label:
            forms.add(label)

    for li in entry_elem.xpath(".//ul[contains(@class, 'synonym_list')]/li"):
        text = _clean_synonym(
            "".join(li.itertext()),
            variant_settings.strip_canonical_suffix,
        )
        if text:
            forms.add(text)

    expanded: Set[str] = set()
    for form in forms:
        expanded.update(
            expand_surface_forms(
                form,
                expand_plurals=variant_settings.expand_plurals,
                expand_verbs=variant_settings.expand_verbs,
                min_length=variant_settings.min_surface_form_length,
            )
        )
    return {
        f.strip()
        for f in expanded
        if len(f.strip()) >= variant_settings.min_surface_form_length
    }


def build_term_index(
    encyclopedia_html_path: Path,
    settings: AnnotateSettings,
) -> TermIndex:
    root = lxml_html.parse(str(encyclopedia_html_path)).getroot()
    entries_by_id: Dict[str, EncyclopediaEntry] = {}
    phrase_to_entry_id: Dict[str, str] = {}
    ignore_case = settings.matching.ignore_case

    for entry_elem in root.xpath(".//div[@role='ami_entry']"):
        wikidata_id = (
            entry_elem.get("data-entry-id")
            or entry_elem.get("wikidataID")
            or ""
        ).strip()
        if not wikidata_id:
            continue

        canonical = (entry_elem.get("term") or wikidata_id).strip()
        surface_forms = _collect_surface_forms(entry_elem, settings)
        if not surface_forms:
            continue

        fragment = _fragment_for_entry(wikidata_id, settings)
        href = _href_for_entry(fragment, settings)
        entries_by_id[wikidata_id] = EncyclopediaEntry(
            wikidata_id=wikidata_id,
            canonical_term=canonical,
            fragment=fragment,
            href=href,
            surface_forms=frozenset(surface_forms),
        )

        for form in surface_forms:
            key = form.lower() if ignore_case else form
            if key not in phrase_to_entry_id:
                phrase_to_entry_id[key] = wikidata_id

    sorted_phrases = sorted(
        phrase_to_entry_id.keys(),
        key=lambda p: (len(p), p.lower()),
        reverse=True,
    )
    return TermIndex(
        entries_by_id=entries_by_id,
        phrase_to_entry_id=phrase_to_entry_id,
        sorted_phrases=sorted_phrases,
    )

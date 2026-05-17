"""Copy encyclopedia source, anchors, fix Wikipedia hrefs, inject styles."""

from __future__ import annotations

import shutil
from pathlib import Path

from lxml import html as lxml_html

from encyclopedia.cabook_annotate.link_normalizer import (
    inject_stylesheet,
    normalize_links_in_tree,
    stylesheet_href_for_html,
)
from encyclopedia.config_loader import AnnotateSettings


def prepare_encyclopedia_html(settings: AnnotateSettings) -> Path:
    paths = settings.paths
    prep = settings.encyclopedia_prepare
    dest = paths.prepared_encyclopedia_html
    dest.parent.mkdir(parents=True, exist_ok=True)

    source = paths.encyclopedia_input_html
    if not source.exists():
        raise FileNotFoundError(f"Encyclopedia input not found: {source}")

    if not dest.exists() or prep.overwrite_prepared:
        shutil.copy2(source, dest)
    elif prep.copy_source_if_missing and not dest.exists():
        shutil.copy2(source, dest)

    _postprocess_encyclopedia(dest, settings)
    return dest


def _postprocess_encyclopedia(encyclopedia_path: Path, settings: AnnotateSettings) -> None:
    parser = lxml_html.HTMLParser(encoding="utf-8")
    tree = lxml_html.parse(str(encyclopedia_path), parser)
    root = tree.getroot()
    changed = False

    attr = settings.encyclopedia_prepare.entry_id_attribute
    fragment_tpl = settings.links.fragment_template
    for entry in root.xpath(".//div[@role='ami_entry']"):
        wikidata_id = (entry.get("data-entry-id") or entry.get("wikidataID") or "").strip()
        if not wikidata_id:
            continue
        anchor_id = fragment_tpl.format(wikidata_id=wikidata_id)
        if entry.get(attr) != anchor_id:
            entry.set(attr, anchor_id)
            changed = True

    hrefs_fixed, classes_applied = normalize_links_in_tree(root, settings)
    if hrefs_fixed or classes_applied:
        changed = True

    css_href = stylesheet_href_for_html(encyclopedia_path, settings.paths.link_css)
    inject_stylesheet(root, css_href)
    changed = True

    if changed:
        tree.write(
            str(encyclopedia_path),
            encoding="utf-8",
            method="html",
            pretty_print=False,
        )

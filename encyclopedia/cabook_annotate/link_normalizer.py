"""Fix Wikipedia hrefs and apply CSS classes by link type."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple
from urllib.parse import urlparse

from lxml import etree
from lxml import html as lxml_html

from encyclopedia.config_loader import AnnotateSettings


def absolutize_wikipedia_href(href: str, wikipedia_base_url: str) -> str:
    if not href:
        return href
    if href.startswith("/wiki/") or href.startswith("/w/"):
        return wikipedia_base_url.rstrip("/") + href
    return href


def _append_class(element: etree._Element, class_name: str) -> None:
    existing = (element.get("class") or "").split()
    if class_name not in existing:
        existing.append(class_name)
        element.set("class", " ".join(existing))


def _classify_link(href: str, settings: AnnotateSettings) -> str | None:
    if href.startswith("#"):
        return settings.links.internal_link_class
    parsed = urlparse(href)
    host = (parsed.netloc or "").lower()
    if "wikidata.org" in host:
        return settings.links.wikidata_link_class
    if "wikipedia.org" in host:
        return settings.links.wikipedia_link_class
    base_host = urlparse(settings.links.wikipedia_base_url).netloc.lower()
    if base_host and host == base_host:
        return settings.links.wikipedia_link_class
    return None


def normalize_links_in_tree(root: etree._Element, settings: AnnotateSettings) -> Tuple[int, int]:
    """Return (hrefs_fixed, classes_applied). Skips ca-encyclopedia-link anchors."""
    ca_class = settings.links.link_class
    hrefs_fixed = 0
    classes_applied = 0

    for anchor in root.xpath(".//*[@href]"):
        classes = anchor.get("class") or ""
        if ca_class in classes.split():
            continue

        href = anchor.get("href") or ""
        fixed = absolutize_wikipedia_href(href, settings.links.wikipedia_base_url)
        if fixed != href:
            anchor.set("href", fixed)
            hrefs_fixed += 1
            href = fixed

        if "wikipedia-link" in classes.split():
            _append_class(anchor, settings.links.wikipedia_link_class)
            classes_applied += 1
            continue
        if "wikidata-link" in classes.split():
            _append_class(anchor, settings.links.wikidata_link_class)
            classes_applied += 1
            continue

        link_class = _classify_link(href, settings)
        if link_class:
            _append_class(anchor, link_class)
            classes_applied += 1

    return hrefs_fixed, classes_applied


def normalize_links_in_file(html_path: Path, settings: AnnotateSettings) -> Tuple[int, int]:
    parser = lxml_html.HTMLParser(encoding="utf-8")
    tree = lxml_html.parse(str(html_path), parser)
    hrefs_fixed, classes_applied = normalize_links_in_tree(tree.getroot(), settings)
    if hrefs_fixed or classes_applied:
        tree.write(str(html_path), encoding="utf-8", method="html", pretty_print=False)
    return hrefs_fixed, classes_applied


def inject_stylesheet(root: etree._Element, css_href: str) -> None:
    head = root.find(".//head")
    if head is None:
        head = etree.Element("head")
        root.insert(0, head)
    for old in head.xpath(".//link[@rel='stylesheet']"):
        href = old.get("href") or ""
        if "cabook_links.css" in href:
            head.remove(old)
    existing = head.xpath(f".//link[@rel='stylesheet' and @href='{css_href}']")
    if existing:
        return
    link = etree.Element("link")
    link.set("rel", "stylesheet")
    link.set("href", css_href)
    link.set("type", "text/css")
    head.append(link)


def stylesheet_href_for_html(html_path: Path, css_path: Path) -> str:
    rel = os.path.relpath(css_path.resolve(), html_path.parent.resolve())
    return Path(rel).as_posix()


def inject_stylesheet_for_output(html_path: Path, css_path: Path) -> None:
    parser = lxml_html.HTMLParser(encoding="utf-8")
    tree = lxml_html.parse(str(html_path), parser)
    root = tree.getroot()
    css_href = stylesheet_href_for_html(html_path, css_path)
    inject_stylesheet(root, css_href)
    tree.write(str(html_path), encoding="utf-8", method="html", pretty_print=False)

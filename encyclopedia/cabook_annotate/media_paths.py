"""Rewrite relative book image paths for annotated HTML output location."""

from __future__ import annotations

import os
from pathlib import Path

from lxml import html as lxml_html

from encyclopedia.config_loader import AnnotateSettings


def _media_file_for_src(src: str, media_dir: Path, media_prefix: str) -> Path | None:
    raw = src.strip()
    if not raw or raw.startswith(("http://", "https://", "data:", "//")):
        return None

    path = Path(raw)
    if path.is_absolute():
        return path if path.is_file() else None

    candidates: list[Path] = []
    prefix = media_prefix.strip("/")
    parts = path.parts
    if prefix and parts and parts[0] == prefix:
        candidates.append(media_dir.joinpath(*parts[1:]))
    candidates.append(media_dir / path.name)
    candidates.append(media_dir / raw)

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return None


def rewrite_media_src_in_tree(
    root,
    html_path: Path,
    media_dir: Path,
    media_prefix: str,
) -> int:
    """Point img/@src at book media files relative to the output HTML file."""
    html_dir = html_path.parent.resolve()
    updated = 0

    for img in root.xpath(".//img[@src]"):
        src = img.get("src") or ""
        media_file = _media_file_for_src(src, media_dir, media_prefix)
        if media_file is None:
            continue
        rel = Path(os.path.relpath(media_file, html_dir)).as_posix()
        if img.get("src") != rel:
            img.set("src", rel)
            updated += 1

    return updated


def rewrite_media_in_file(html_path: Path, settings: AnnotateSettings) -> int:
    media_dir = settings.paths.book_media_dir
    if not media_dir.is_dir():
        raise FileNotFoundError(f"Book media directory not found: {media_dir}")

    parser = lxml_html.HTMLParser(encoding="utf-8")
    tree = lxml_html.parse(str(html_path), parser)
    updated = rewrite_media_src_in_tree(
        tree.getroot(),
        html_path,
        media_dir,
        settings.media.media_src_prefix,
    )
    if updated:
        tree.write(str(html_path), encoding="utf-8", method="html", pretty_print=False)
    return updated

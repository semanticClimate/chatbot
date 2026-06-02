"""Annotated book HTML for iframe viewers (FastAPI and browser client)."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from urllib.parse import unquote

from bs4 import BeautifulSoup

from climate_streamlit.config_loader import AppSettings
from climate_streamlit.html_sectioning import annotate_html_with_section_ids
from climate_streamlit.rag.encyclopedia_document import (
    annotated_book_path,
    link_css_path,
)

_PKG_DIR = Path(__file__).resolve().parent.parent
_ASSETS = _PKG_DIR / "assets"


def package_assets_dir() -> Path:
    """climate_streamlit/assets (book iframe CSS/JS)."""
    return _ASSETS


def inject_book_viewer_assets(
    annotated_html: str,
    assets_dir: Path | None = None,
    *,
    include_encyclopedia_links: bool = False,
) -> str:
    """
    Inject iframe viewer CSS (including visible § labels) and jump script.

    See docs/HTML_SECTION_NESTING.md — "Visible section numbers in the viewer".
    """
    assets = assets_dir or _ASSETS
    hi_css = (assets / "book_iframe_highlight.css").read_text(encoding="utf-8")
    highlight_css = f"<style>\n{hi_css}\n</style>"

    extra_head = ""
    if include_encyclopedia_links:
        css_path = link_css_path()
        if css_path.is_file():
            link_css = css_path.read_text(encoding="utf-8")
            extra_head += f"<style>\n{link_css}\n</style>"

    jump_js = (assets / "book_iframe_jump.js").read_text(encoding="utf-8")
    jump_script = f"<script>\n{jump_js}\n</script>"
    if include_encyclopedia_links:
        enc_js = (assets / "book_encyclopedia_links.js").read_text(encoding="utf-8")
        jump_script += f"\n<script>\n{enc_js}\n</script>"

    out = annotated_html
    head_inject = highlight_css + extra_head
    if "</head>" in out:
        out = out.replace("</head>", head_inject + "</head>")
    else:
        out = head_inject + out

    if "</body>" in out:
        out = out.replace("</body>", jump_script + "</body>")
    else:
        out += jump_script

    return out


def inline_local_images(html: str, base_dir: Path) -> str:
    """
    Inline local <img src="media/..."> as data URIs so the document works when
    served from an arbitrary URL path (iframe src), matching Streamlit behavior.
    """
    soup = BeautifulSoup(html, "html.parser")
    base_dir = base_dir.resolve()

    for img in soup.find_all("img"):
        src = img.get("src", "").strip()
        if (
            not src
            or src.startswith(("data:", "http://", "https://", "//"))
            or src.startswith("#")
        ):
            continue

        clean_src = unquote(src.split("#", 1)[0].split("?", 1)[0])
        image_path = (base_dir / clean_src).resolve()
        project_root = _PKG_DIR.parent.resolve()
        try:
            image_path.relative_to(project_root)
        except ValueError:
            continue
        if not image_path.is_file():
            continue

        mime_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
        img["src"] = f"data:{mime_type};base64,{encoded}"

    return str(soup)


def resolve_book_html_path(settings: AppSettings) -> Path:
    """Prefer pipeline-annotated CABook when present."""
    annotated = annotated_book_path(settings)
    if annotated.is_file():
        return annotated
    return settings.html_path


def build_annotated_book_document(settings: AppSettings) -> str:
    """
    Full HTML document: section anchors, inlined images, iframe CSS/JS from assets.
    Uses encyclopedia-linked CABook HTML when the annotation pipeline output exists.
    """
    html_file = resolve_book_html_path(settings)
    raw = html_file.read_text(encoding="utf-8")
    annotated = annotate_html_with_section_ids(raw)
    annotated = inline_local_images(annotated, html_file.parent)
    has_encyclopedia_links = "ca-encyclopedia-link" in annotated
    return inject_book_viewer_assets(
        annotated,
        include_encyclopedia_links=has_encyclopedia_links,
    )

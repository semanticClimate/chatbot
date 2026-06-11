"""Annotated book HTML for iframe viewers (FastAPI and browser client)."""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from urllib.parse import unquote

from bs4 import BeautifulSoup

from climate_streamlit.config_loader import AppSettings
from climate_streamlit.html_sectioning import annotate_html_with_section_ids


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
        try:
            image_path.relative_to(base_dir)
        except ValueError:
            continue
        if not image_path.is_file():
            continue

        mime_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
        img["src"] = f"data:{mime_type};base64,{encoded}"

    return str(soup)


def build_annotated_book_document(settings: AppSettings) -> str:
    """
    Full HTML document: section anchors, inlined images, iframe CSS/JS from assets.
    """
    html_file = settings.html_path
    raw = html_file.read_text(encoding="utf-8")
    annotated = annotate_html_with_section_ids(raw, html_format=settings.html_format)
    annotated = inline_local_images(annotated, html_file.parent)

    pkg_dir = Path(__file__).resolve().parent.parent
    hi_css = (pkg_dir / "assets" / "book_iframe_highlight.css").read_text(encoding="utf-8")
    highlight_css = f"<style>\n{hi_css}\n</style>"

    jump_js = (pkg_dir / "assets" / "book_iframe_jump.js").read_text(encoding="utf-8")
    jump_script = f"<script>\n{jump_js}\n</script>"

    if "</head>" in annotated:
        annotated = annotated.replace("</head>", highlight_css + "</head>")
    else:
        annotated = highlight_css + annotated

    if "</body>" in annotated:
        annotated = annotated.replace("</body>", jump_script + "</body>")
    else:
        annotated += jump_script

    return annotated

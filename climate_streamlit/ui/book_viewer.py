"""Annotated HTML book iframe and jump triggers."""

from __future__ import annotations

import json
from typing import Optional

import streamlit as st
import streamlit.components.v1 as components

from config_loader import AppSettings


def render_book_viewer(
    book_html: str,
    settings: AppSettings,
    target_anchor_id: Optional[str] = None,
    target_section: Optional[str] = None,
    heading_id: str = "",
    jump_type: str = "section",
):
    """
    Renders the annotated book HTML.

    When jump_type == "para":
      fires  ca-jump-para  with anchor_id  →  highlights EXACT paragraph

    When jump_type == "section" (legacy):
      fires  ca-jump  with section number  →  highlights whole ca-section div
    """
    height = settings.book_viewer_height
    trigger = ""
    if jump_type == "para" and target_anchor_id:
        payload = json.dumps({
            "type":      "ca-jump-para",
            "anchor_id": target_anchor_id,
            "section":   target_section or "",
        })
        trigger = f"""
<script>
(function() {{
    function fire() {{
        window.dispatchEvent(new MessageEvent('message', {{ data: {payload} }}));
    }}
    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', fire);
    }} else {{
        fire();
    }}
}})();
</script>
"""
    elif jump_type == "section" and target_section:
        payload = json.dumps({
            "type":       "ca-jump",
            "section":    target_section,
            "keywords":   [],
            "heading_id": heading_id,
        })
        trigger = f"""
<script>
(function() {{
    function fire() {{
        window.dispatchEvent(new MessageEvent('message', {{ data: {payload} }}));
    }}
    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', fire);
    }} else {{
        fire();
    }}
}})();
</script>
"""

    final = book_html
    if trigger:
        if "</body>" in final:
            final = final.replace("</body>", trigger + "</body>")
        else:
            final += trigger

    components.html(final, height=height, scrolling=True)

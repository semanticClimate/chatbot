"""PDF data URI and optional iframe viewer."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import streamlit as st
import streamlit.components.v1 as components


@st.cache_data
def load_pdf_data_uri(pdf_path: str) -> str:
    raw = Path(pdf_path).read_bytes()
    b64 = base64.b64encode(raw).decode("utf-8")
    return f"data:application/pdf;base64,{b64}"


def render_pdf_viewer(
    pdf_data_uri: str,
    search_query: str = "",
    page_number: Optional[int] = None,
    height: int = 760,
):
    fragment = "#toolbar=1&navpanes=0&scrollbar=1&view=FitH"
    if page_number and page_number > 0:
        fragment += f"&page={int(page_number)}"
    if search_query:
        fragment += f"&search={quote(search_query)}"
    src = pdf_data_uri + fragment
    components.html(
        f'<iframe src="{src}" width="100%" height="{height}" style="border:none;border-radius:10px;"></iframe>',
        height=height + 8,
        scrolling=False,
    )

"""
Climate Academy Chatbot — Paragraph-Level RAG + Precise Source Navigation
=========================================================================

Run: streamlit run app.py
"""

from __future__ import annotations

import streamlit as st

from config_loader import get_settings
from llm.groq_client import load_groq
from pdf.viewer import load_pdf_data_uri
from rag.indexing import build_knowledge_base, get_annotated_book_html
from styling import apply_streamlit_css
from ui.chat_column import render_book_panel, render_chat_column
from ui.session import init_session
from ui.sidebar import render_sidebar

settings = get_settings()

st.set_page_config(
    page_title=settings.page_title,
    page_icon=settings.page_icon,
    layout=settings.layout,
    initial_sidebar_state=settings.initial_sidebar_state,
)
apply_streamlit_css()
init_session(settings)

collection, embedder = build_knowledge_base(settings)
groq_client = load_groq()

if settings.html_path.is_file():
    BOOK_HTML = get_annotated_book_html(
        str(settings.html_path),
        str(settings.base_dir),
    )
else:
    BOOK_HTML = (
        "<p style='color:red;padding:2rem'>⚠️ Book HTML not found. "
        f"Check paths in config/app.defaults.toml (expected `{settings.html_path}`).</p>"
    )

pdf_path_str = str(settings.pdf_path)
BOOK_PDF_URI = load_pdf_data_uri(pdf_path_str) if settings.pdf_path.is_file() else ""

render_sidebar(settings)

col_chat, col_book = st.columns([5, 7], gap="small")

with col_chat:
    render_chat_column(
        settings,
        collection,
        embedder,
        groq_client,
        pdf_path_str,
        settings.pdf_path.is_file(),
    )

with col_book:
    render_book_panel(settings, BOOK_HTML)

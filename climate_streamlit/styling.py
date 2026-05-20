"""Inject Streamlit shell CSS from external file."""

from __future__ import annotations

from pathlib import Path

import streamlit as st


def apply_streamlit_css() -> None:
    base = Path(__file__).resolve().parent
    css_path = base / "assets" / "app_streamlit.css"
    css_text = css_path.read_text(encoding="utf-8")
    st.markdown(f"<style>\n{css_text}\n</style>", unsafe_allow_html=True)

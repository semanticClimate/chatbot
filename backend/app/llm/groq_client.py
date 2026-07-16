"""Groq API client."""

from __future__ import annotations

import os
from groq import Groq

try:
    import streamlit as st
except ModuleNotFoundError:  # FastAPI-only environment
    st = None


def load_groq_from_env() -> Groq:
    """
    Create Groq client from environment only (for FastAPI / workers).
    Does not read Streamlit secrets.
    """
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Export it in the environment before starting the API server."
        )
    return Groq(api_key=api_key)


def load_groq():
    if st is None:
        raise RuntimeError(
            "Streamlit is not installed. Use load_groq_from_env() in API/server contexts."
        )
    api_key = os.environ.get("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", "")
    if not api_key:
        st.error(
            "⚠️ GROQ_API_KEY not set.\n\n"
            "Add to .streamlit/secrets.toml:\n   GROQ_API_KEY = 'gsk_...'"
        )
        st.stop()
    return Groq(api_key=api_key)

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
    
    from dotenv import load_dotenv
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    load_dotenv(os.path.join(root_dir, ".env"), override=True)
    load_dotenv(os.path.join(root_dir, "venv", ".env"), override=True)

    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        st.error(
            "⚠️ GROQ_API_KEY not set.\n\n"
            "Please ensure it is set in your .env file."
        )
        st.stop()
    return Groq(api_key=api_key)

"""Groq API client."""

from __future__ import annotations

import os

import streamlit as st
from groq import Groq


def load_groq():
    api_key = os.environ.get("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", "")
    if not api_key:
        st.error(
            "⚠️ GROQ_API_KEY not set.\n\n"
            "Add to .streamlit/secrets.toml:\n   GROQ_API_KEY = 'gsk_...'"
        )
        st.stop()
    return Groq(api_key=api_key)

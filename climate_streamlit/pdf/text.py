"""PDF search query and text helpers."""

from __future__ import annotations

import re


def make_pdf_search_query(text: str, max_words: int) -> str:
    if not text:
        return ""
    cleaned = " ".join(text.replace("\n", " ").split())
    words = cleaned.split(" ")
    return " ".join(words[:max_words]).strip()


def norm_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def keyword_set(text: str, max_words: int) -> set[str]:
    words = [w for w in norm_text(text).split(" ") if len(w) >= 5]
    return set(words[:max_words])

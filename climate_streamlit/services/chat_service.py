"""RAG + LLM orchestration shared by the FastAPI server."""

from __future__ import annotations

import time
from typing import Any, Optional

from climate_streamlit.config_loader import AppSettings
from climate_streamlit.llm.ask import ask_groq
from climate_streamlit.pdf.index import map_chunks_to_pdf_core
from climate_streamlit.rag.retrieve import retrieve


def run_retrieve(
    query: str,
    collection,
    embedder,
    settings: AppSettings,
    top_k: Optional[int] = None,
) -> list[dict]:
    return retrieve(query, collection, embedder, settings, top_k=top_k)


def run_ask(
    question: str,
    conversation: list[dict],
    collection,
    embedder,
    groq_client,
    settings: AppSettings,
    *,
    top_k: Optional[int] = None,
) -> dict[str, Any]:
    """
    Full retrieval + PDF mapping + Groq completion.
    Returns blocks, sources, operator_detail, timings_ms.
    """
    t0 = time.perf_counter()
    chunks = retrieve(question, collection, embedder, settings, top_k=top_k)
    t1 = time.perf_counter()

    pdf_chunk_map: dict = {}
    if settings.pdf_path.is_file():
        pdf_chunk_map = map_chunks_to_pdf_core(
            chunks,
            str(settings.pdf_path),
            settings.pdf_keyword_max_words,
        )
    t2 = time.perf_counter()

    answer = ask_groq(
        groq_client,
        chunks,
        conversation,
        question,
        settings,
        pdf_chunk_map=pdf_chunk_map or None,
    )
    t3 = time.perf_counter()

    total_ms = (t3 - t0) * 1000.0
    return {
        "blocks": answer.get("blocks", []),
        "sources": answer.get("sources", []),
        "operator_detail": answer.get("operator_detail"),
        "timings_ms": {
            "retrieve": round((t1 - t0) * 1000.0, 3),
            "pdf_map": round((t2 - t1) * 1000.0, 3),
            "llm": round((t3 - t2) * 1000.0, 3),
            "total": round(total_ms, 3),
        },
    }

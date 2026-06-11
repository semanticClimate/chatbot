"""Embedder, Chroma collection build, and annotated book HTML."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import chromadb
try:
    import streamlit as st
except ModuleNotFoundError:  # FastAPI-only environment
    class _StreamlitShim:
        @staticmethod
        def cache_resource(fn):
            return fn

        @staticmethod
        def cache_data(fn):
            return fn

    st = _StreamlitShim()
from chromadb.config import Settings as ChromaSettings
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

from climate_streamlit.config_loader import AppSettings
from climate_streamlit.html_sectioning import annotate_html_with_section_ids, parse_html_path_to_chunks


def load_embedder():
    return ONNXMiniLM_L6_V2()


def build_knowledge_base_core(
    settings: AppSettings,
    *,
    progress_callback: Optional[Callable[[float, str], None]] = None,
):
    """
    Connect to Chroma, embed and index the HTML book when the collection is empty.
    No Streamlit UI. Raises FileNotFoundError / RuntimeError if inputs are invalid.
    """
    embedder = load_embedder()
    chroma = chromadb.PersistentClient(
        path=settings.chroma_dir,
        settings=ChromaSettings(anonymized_telemetry=False),
    )
    collection = chroma.get_or_create_collection(
        name=settings.collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    if collection.count() > 0:
        return collection, embedder

    html_path = settings.html_path
    if not html_path.is_file():
        raise FileNotFoundError(f"HTML book not found at `{html_path}`")

    indexed = parse_html_path_to_chunks(
        html_path,
        chunk_size=0,
        chunk_overlap=0,
        html_format=settings.html_format,
    )
    if not indexed:
        raise RuntimeError("No paragraphs extracted from HTML.")

    n = len(indexed)
    batch_size = settings.indexing_batch_size
    for i in range(0, n, batch_size):
        batch = indexed[i : i + batch_size]
        docs = [c.document for c in batch]
        collection.add(
            documents=docs,
            embeddings=embedder(docs),
            ids=[c.chunk_id if c.chunk_id else f"chunk_{i+j}" for j, c in enumerate(batch)],
            metadatas=[
                {
                    "section_number": c.section_number,
                    "section_title":  c.section_title or "",
                    "chunk_index":    str(c.chunk_index),
                    "heading_id":     c.heading_id or "",
                    "chunk_id":       c.chunk_id or "",
                    "anchor_id":      c.anchor_id or "",
                }
                for c in batch
            ],
        )
        if progress_callback:
            pct = min(100, int((i + batch_size) / n * 100))
            progress_callback(
                min(1.0, (i + batch_size) / n),
                f"Embedding... {pct}%",
            )
    return collection, embedder


@st.cache_data
def get_annotated_book_html(html_path: str, base_dir_str: str) -> str:
    """
    Reads the raw HTML, runs annotate_html_with_section_ids,
    injects highlight CSS and the postMessage listener.
    """
    base_dir = Path(base_dir_str)
    raw = Path(html_path).read_text(encoding="utf-8")
    annotated = annotate_html_with_section_ids(raw)

    hi_css = (base_dir / "assets" / "book_iframe_highlight.css").read_text(encoding="utf-8")
    highlight_css = f"<style>\n{hi_css}\n</style>"

    jump_js = (base_dir / "assets" / "book_iframe_jump.js").read_text(encoding="utf-8")
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


@st.cache_resource
def build_knowledge_base(settings: AppSettings):
    if not hasattr(st, "progress"):
        raise RuntimeError("build_knowledge_base() requires Streamlit runtime.")
    bar = st.progress(0, text="🔄 Loading knowledge base...")
    try:

        def _cb(fraction: float, text: str) -> None:
            bar.progress(fraction, text=text)

        with st.spinner("📄 Indexing the book (first run only; may take several minutes)..."):
            collection, embedder = build_knowledge_base_core(
                settings,
                progress_callback=_cb,
            )
    except FileNotFoundError as e:
        bar.empty()
        st.error(f"⚠️ {e}")
        st.stop()
    except RuntimeError as e:
        bar.empty()
        st.error(str(e))
        st.stop()
    else:
        bar.empty()

    st.sidebar.success(f"✅ {collection.count():,} paragraph chunks loaded.")
    return collection, embedder

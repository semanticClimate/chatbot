"""Embedder, Chroma collection build, and annotated book HTML."""

from __future__ import annotations

from pathlib import Path

import chromadb
import streamlit as st
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

from config_loader import AppSettings
from html_sectioning import annotate_html_with_section_ids, parse_html_path_to_chunks


def load_embedder():
    return ONNXMiniLM_L6_V2()


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
    embedder = load_embedder()
    chroma = chromadb.PersistentClient(path=settings.chroma_dir)
    collection = chroma.get_or_create_collection(
        name=settings.collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    if collection.count() > 0:
        st.sidebar.success(f"✅ {collection.count():,} paragraph chunks loaded.")
        return collection, embedder

    html_path = settings.html_path
    if not html_path.is_file():
        st.error(f"⚠️ HTML book not found at `{html_path}`.")
        st.stop()

    with st.spinner("📄 Parsing HTML book into paragraphs..."):
        indexed = parse_html_path_to_chunks(html_path, chunk_size=0, chunk_overlap=0)
    if not indexed:
        st.error("No paragraphs extracted from HTML.")
        st.stop()

    bar = st.progress(0, text="🔄 Building knowledge base (first run only)...")
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
        bar.progress(
            min(1.0, (i + batch_size) / n),
            text=f"🔄 Embedding... {min(100, int((i + batch_size) / n * 100))}%",
        )
    bar.empty()
    st.success(f"✅ Knowledge base ready — {collection.count():,} paragraph chunks indexed!")
    return collection, embedder

"""
Climate Academy Chatbot — Paragraph-Level RAG + Precise Source Navigation
=========================================================================
Author: Udita Agarwal 2026  |  Licence: Apache 2.0

What's new vs the previous version
────────────────────────────────────
1. CHUNKING      — Every paragraph is its own chunk (not word-window slices).
                   Each chunk carries chunk_id + anchor_id.

2. RETRIEVAL     — Returns TOP_K chunks; each one = one answer point.

3. LLM PROMPT    — Strictly enforces one point = one chunk in structured JSON.

4. ANSWER FORMAT — Structured point-by-point cards in the UI, each with its
                   own "View Source" button that jumps to the EXACT paragraph.

5. NAVIGATION    — postMessage now carries anchor_id so the iframe highlights
                   the exact <p> / <ul> element, NOT the whole section wrapper.

Run: streamlit run app.py
"""

import json
import os
import base64
import mimetypes
import zipfile
import fitz
from pathlib import Path
from typing import Optional
from urllib.parse import quote, unquote
from uuid import uuid4

import chromadb
import streamlit as st
import streamlit.components.v1 as components
from bs4 import BeautifulSoup
from chromadb.config import Settings
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2
from groq import Groq

from html_sectioning import (
    annotate_html_with_section_ids,
    format_passage_for_prompt,
    parse_html_path_to_chunks,
)
from db import init_db, log_interaction, update_feedback, get_all_logs, get_logs_csv_string

# ─────────────────────────────────────────────────────
# PAGE CONFIG — must be the very first Streamlit call
# ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="Climate Academy Chatbot",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────
init_db()
BASE_DIR        = Path(__file__).resolve().parent
ROOT_DIR        = BASE_DIR.parent
HTML_PATH       = Path(ROOT_DIR, "input", "full_student_book.html")
DOCX_PATH       = Path(ROOT_DIR, "input", "2025_10", "full_student_book.docx")
PDF_PATH        = Path(ROOT_DIR, "input", "2025_10", "climate_academy_book.pdf")
CHROMA_DIR      = str(Path(ROOT_DIR, "chroma_db"))
COLLECTION_NAME = "climate_academy_paragraphs_v2"   # new name → forces re-index
TOP_K           = 14   # retrieve more context for higher answer quality
EMBED_MODEL     = "all-MiniLM-L6-v2 (ONNX)"
GROQ_MODEL      = "llama-3.3-70b-versatile"
BOOK_VIEWER_HEIGHT = 760

# ─────────────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────────────
st.markdown("""
<style>
:root {
    --bg-soft: #f2f6f3;
    --surface: #ffffff;
    --text-900: #15231b;
    --text-600: #4f6257;
    --line: #d9e5dd;
    --brand: #1f6a43;
    --brand-dark: #185235;
    --mint: #e8f2eb;
    --accent: #b55d2d;
}

.stApp {
    background:
      radial-gradient(1200px 400px at -20% -10%, #e6f1ea 0%, transparent 65%),
      radial-gradient(900px 380px at 115% 0%, #f4efe4 0%, transparent 62%),
      var(--bg-soft);
}

header[data-testid="stHeader"] { display: none !important; }
div[data-testid="stToolbar"] { display: none !important; }
#MainMenu { visibility: hidden !important; }
footer { visibility: hidden !important; }

.block-container {
    max-width: 100% !important;
    padding-top: 0.75rem !important;
    padding-bottom: 0.25rem !important;
    padding-left: 1rem !important;
    padding-right: 1rem !important;
}

.panel-header {
    background: linear-gradient(135deg, var(--brand), var(--brand-dark));
    color: #fff;
    border-radius: 14px;
    padding: 12px 14px;
    margin-bottom: 10px;
    box-shadow: 0 12px 24px rgba(14, 40, 27, 0.14);
}

.panel-title {
    margin: 0;
    font-size: 16px;
    font-weight: 700;
    letter-spacing: 0.2px;
}

.panel-subtitle {
    margin: 3px 0 0;
    font-size: 12px;
    opacity: 0.9;
}

.section-label {
    margin: 6px 0 8px;
    color: var(--text-600);
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.2px;
}

div[data-testid="stRadio"] label p {
    font-size: 13px !important;
    color: var(--text-900);
    font-weight: 600;
}

div[data-testid="stButton"] > button {
    border-radius: 12px;
    border: 1px solid var(--line);
    background: var(--surface);
    color: var(--text-900);
    font-weight: 600;
    min-height: 40px;
    transition: all 0.2s ease;
}

div[data-testid="stButton"] > button:hover {
    border-color: #b9d0c1;
    transform: translateY(-1px);
    box-shadow: 0 8px 16px rgba(31, 106, 67, 0.12);
}

.msg-row-bot  { display:flex; align-items:flex-start; gap:9px; margin:8px 0; }
.msg-row-user { display:flex; justify-content:flex-end; margin:8px 0; }

.avatar {
    width: 32px;
    height: 32px;
    border-radius: 10px;
    background: linear-gradient(145deg, var(--brand), #2a8252);
    color: white;
    display:flex;
    align-items:center;
    justify-content:center;
    font-size: 11px;
    font-weight: 700;
    flex-shrink:0;
}

.bubble-bot {
    background: var(--surface);
    color: var(--text-900);
    border-radius: 14px 14px 14px 4px;
    padding: 10px 13px;
    margin: 2px 0;
    font-size: 14px;
    line-height: 1.62;
    max-width: 96%;
    border: 1px solid var(--line);
    box-shadow: 0 6px 14px rgba(25, 44, 32, 0.06);
}

.bubble-user {
    background: linear-gradient(145deg, var(--brand), #1a5a39);
    color: #ffffff;
    border-radius: 14px 14px 4px 14px;
    padding: 10px 13px;
    margin: 2px 0 2px auto;
    font-size: 14px;
    line-height: 1.62;
    max-width: 90%;
    text-align: right;
    box-shadow: 0 10px 18px rgba(25, 63, 43, 0.2);
}

.point-card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-left: 5px solid var(--brand);
    border-radius: 12px;
    padding: 11px 13px;
    margin: 8px 0;
    font-size: 13.5px;
    line-height: 1.58;
    box-shadow: 0 8px 16px rgba(22, 45, 32, 0.06);
}

.point-title {
    font-weight: 700;
    font-size: 14px;
    color: var(--text-900);
    margin-bottom: 4px;
}

.point-body {
    color: #2d3a33;
    margin-bottom: 8px;
}

.source-meta {
    font-size: 11.5px;
    color: var(--text-600);
    border-top: 1px solid #edf2ee;
    padding-top: 6px;
}

.disclaimer {
    text-align: center;
    font-size: 11px;
    color: #6d7f73;
    margin-top: 8px;
    line-height: 1.5;
}

div[data-testid="stChatInput"] {
    margin-top: 0.35rem;
}

div[data-testid="stVerticalBlock"] > div:has(> div > .section-label) {
    margin-bottom: 0.25rem;
}

div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
    gap: 0.55rem;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f1d17 0%, #14261d 100%);
    border-right: 1px solid #233d31;
}

section[data-testid="stSidebar"] * {
    color: #e6f1ea;
}

section[data-testid="stSidebar"] .stButton > button {
    justify-content: flex-start;
    border-radius: 10px;
    border: 1px solid #2d4b3c;
    background: #173326;
    color: #e6f1ea;
}

section[data-testid="stSidebar"] .stButton > button:hover {
    border-color: #3e6852;
    background: #1f3f2f;
    box-shadow: none;
    transform: none;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────
# ANNOTATED BOOK HTML — built once, cached
# ─────────────────────────────────────────────────────
def ensure_html_media_assets(html_path: Path, docx_path: Path) -> None:
    """
    Pandoc/Word HTML exports reference images as media/image*.png. If that
    folder was not checked in, recover the images from the source .docx.
    """
    media_dir = html_path.parent / "media"
    if media_dir.is_dir() and any(media_dir.iterdir()):
        return
    if not docx_path.is_file():
        return

    media_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(docx_path) as docx:
        for item in docx.infolist():
            if item.is_dir() or not item.filename.startswith("word/media/"):
                continue

            target = media_dir / Path(item.filename).name
            if target.exists():
                continue
            with docx.open(item) as src, target.open("wb") as dst:
                dst.write(src.read())


def inline_local_images(html: str, base_dir: Path) -> str:
    """
    Streamlit components render inside an iframe, so relative image URLs do not
    resolve against input/full_student_book.html. Inline local images instead.
    """
    soup = BeautifulSoup(html, "html.parser")
    base_dir = base_dir.resolve()

    for img in soup.find_all("img"):
        src = img.get("src", "").strip()
        if (
            not src
            or src.startswith(("data:", "http://", "https://", "//"))
            or src.startswith("#")
        ):
            continue

        clean_src = unquote(src.split("#", 1)[0].split("?", 1)[0])
        image_path = (base_dir / clean_src).resolve()
        try:
            image_path.relative_to(base_dir)
        except ValueError:
            continue
        if not image_path.is_file():
            continue

        mime_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
        img["src"] = f"data:{mime_type};base64,{encoded}"

    return str(soup)


@st.cache_data
def get_annotated_book_html(html_path: str) -> str:
    """
    Reads the raw HTML, runs annotate_html_with_section_ids (which now also
    injects para-* anchor IDs), injects highlight CSS and the postMessage
    listener that handles BOTH section-level and paragraph-level jumps.
    """
    html_file = Path(html_path)
    raw       = html_file.read_text(encoding="utf-8")
    annotated = annotate_html_with_section_ids(raw)
    annotated = inline_local_images(annotated, html_file.parent)

    highlight_css = """
<style>
body {
    font-family: Georgia, "Times New Roman", serif;
    font-size: 15px; line-height: 1.8; color: #1a1a1a;
    width: 100%;
    max-width: none;
    margin: 0;
    box-sizing: border-box;
    padding: 22px 24px 72px;
    background: #fdfcf8;
    overflow-x: hidden;
}
h1 { font-size: 1.7em; color: #1a3a2a; margin-bottom: 0.3em; }
h2 { font-size: 1.35em; color: #1a3a2a; margin-top: 1.6em; }
h3 { font-size: 1.15em; color: #2a4a3a; margin-top: 1.4em; }
h4 { font-size: 1.05em; color: #2a4a3a; margin-top: 1.2em; }
p  { margin: 0.6em 0; }
ul, ol { margin: 0.4em 0 0.6em 1.4em; }
li { margin: 0.25em 0; }
img, table, pre, code { max-width: 100% !important; }

.ca-section {
    margin: 0.3em 0;
    padding: 4px 0 4px 0;
    border-left: 3px solid transparent;
    transition: border-left-color 0.3s ease;
}

/* Section-level highlight (fallback) */
@keyframes ca-flash {
    0%   { background: #ffe566; border-left-color: #e6a817; }
    60%  { background: #fff3c4; border-left-color: #e6a817; }
    100% { background: #fffbe8; border-left-color: #c89614; }
}
.ca-highlight {
    background: #fffbe8 !important;
    border-left: 3px solid #c89614 !important;
    border-radius: 0 6px 6px 0;
    padding-left: 12px !important;
    animation: ca-flash 0.8s ease forwards;
    scroll-margin-top: 32px;
}

/* Paragraph-level highlight — this is what fires from "View Source" */
@keyframes para-flash {
    0%   { background: #ffe566; outline: 2px solid #e6a817; }
    50%  { background: #fff3c4; }
    100% { background: #fffbe8; outline: 2px solid #c89614; }
}
.ca-para-highlight {
    background: #fffbe8 !important;
    outline: 2px solid #c89614;
    border-radius: 4px;
    padding: 2px 4px !important;
    animation: para-flash 0.9s ease forwards;
    scroll-margin-top: 80px;
}
</style>
"""

    # This script listens for postMessage from Streamlit.
    # It handles two jump types:
    #   type = "ca-jump-para"    →  jump to exact paragraph element (anchor_id)
    #   type = "ca-jump"         →  jump to section wrapper (legacy fallback)
    jump_script = """
<script>
window.addEventListener('message', function(e) {
    var data = e.data;
    if (!data || !data.type) return;

    // ── Remove all previous highlights ──────────────────────────────────────
    document.querySelectorAll('.ca-highlight').forEach(function(el) {
        el.classList.remove('ca-highlight');
    });
    document.querySelectorAll('.ca-para-highlight').forEach(function(el) {
        el.classList.remove('ca-para-highlight');
    });

    // ── PARAGRAPH jump (precise — from "View Source" button) ────────────────
    if (data.type === 'ca-jump-para') {
        var anchorId = data.anchor_id || '';
        var target   = anchorId ? document.getElementById(anchorId) : null;

        // Fallback: try section-level wrapper if paragraph not found
        if (!target && data.section) {
            target = document.querySelector('.ca-section[data-section-number="' + data.section + '"]');
            if (target) target.classList.add('ca-highlight');
        } else if (target) {
            target.classList.add('ca-para-highlight');
        }

        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        return;
    }

    // ── SECTION jump (legacy, from chip buttons) ─────────────────────────────
    if (data.type === 'ca-jump') {
        var sec    = data.section;
        var kws    = data.keywords || [];
        var origId = data.heading_id || '';
        var target = null;

        target = document.querySelector('.ca-section[data-section-number="' + sec + '"]');
        if (!target) target = document.querySelector('[data-section-number="' + sec + '"]');
        if (!target) target = document.getElementById('section-' + sec.replace(/\\./g, '-'));
        if (!target && origId) {
            target = document.getElementById(origId);
            if (target) { var w = target.closest('.ca-section'); if (w) target = w; }
        }

        if (target) {
            target.classList.add('ca-highlight');
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }
});
</script>
"""

    if "</head>" in annotated:
        annotated = annotated.replace("</head>", highlight_css + "</head>")
    else:
        annotated = highlight_css + annotated

    if "</body>" in annotated:
        annotated = annotated.replace("</body>", jump_script + "</body>")
    else:
        annotated += jump_script

    return annotated


# ─────────────────────────────────────────────────────
# CACHED RESOURCES
# ─────────────────────────────────────────────────────
@st.cache_resource
def load_embedder():
    return ONNXMiniLM_L6_V2()


@st.cache_resource
def load_groq():
    api_key = os.environ.get("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", "")
    if not api_key:
        st.error(
            "⚠️ GROQ_API_KEY not set.\n\n"
            "Add to .streamlit/secrets.toml:\n   GROQ_API_KEY = 'gsk_...'"
        )
        st.stop()
    return Groq(api_key=api_key)


@st.cache_resource
def build_knowledge_base():
    embedder = load_embedder()
    chroma   = chromadb.PersistentClient(
        path=CHROMA_DIR,
        settings=Settings(anonymized_telemetry=False),
    )
    collection = chroma.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"},
    )
    if collection.count() > 0:
        st.sidebar.success(f"✅ {collection.count():,} paragraph chunks loaded.")
        return collection, embedder

    if not HTML_PATH.is_file():
        st.error(f"⚠️ HTML book not found at `{HTML_PATH}`.")
        st.stop()

    with st.spinner("📄 Parsing HTML book into paragraphs..."):
        indexed = parse_html_path_to_chunks(HTML_PATH, chunk_size=0, chunk_overlap=0)
    if not indexed:
        st.error("No paragraphs extracted from HTML.")
        st.stop()

    bar = st.progress(0, text="🔄 Building knowledge base (first run only)...")
    n = len(indexed)
    for i in range(0, n, 64):
        batch = indexed[i : i + 64]
        docs  = [c.document for c in batch]
        collection.add(
            documents  = docs,
            embeddings = embedder(docs),
            ids        = [c.chunk_id if c.chunk_id else f"chunk_{i+j}" for j, c in enumerate(batch)],
            metadatas  = [
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
        bar.progress(min(1.0, (i + 64) / n),
                     text=f"🔄 Embedding... {min(100, int((i+64)/n*100))}%")
    bar.empty()
    st.success(f"✅ Knowledge base ready — {collection.count():,} paragraph chunks indexed!")
    return collection, embedder


# ─────────────────────────────────────────────────────
# RETRIEVE
# ─────────────────────────────────────────────────────
def retrieve(query: str, collection, embedder):
    """
    Returns a list of dicts, each containing:
      document, section_number, section_title, heading_id, chunk_id, anchor_id
    Ordered by relevance.
    """
    query_vector = embedder([query])[0]
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=TOP_K,
        include=["documents", "distances", "metadatas"],
    )
    docs   = results["documents"][0]
    dists  = results["distances"][0]
    metas  = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)

    triples  = list(zip(docs, dists, metas))
    filtered = [(d, dist, m) for d, dist, m in triples if dist < 1.5]
    use      = filtered if filtered else triples

    chunks = []
    for doc, _dist, meta in use:
        chunks.append({
            "document":       doc,
            "section_number": meta.get("section_number", ""),
            "section_title":  meta.get("section_title", ""),
            "heading_id":     meta.get("heading_id", ""),
            "chunk_id":       meta.get("chunk_id", ""),
            "anchor_id":      meta.get("anchor_id", ""),
        })
    return chunks


def build_sources(chunks: list[dict], pdf_chunk_map: Optional[dict] = None) -> list[dict]:
    """Create unique ordered source list from retrieved chunks."""
    seen = set()
    sources = []
    pdf_chunk_map = pdf_chunk_map or {}
    for c in chunks:
        chunk_id = c.get("chunk_id", "")
        if not chunk_id or chunk_id in seen:
            continue
        seen.add(chunk_id)
        pdf_map = pdf_chunk_map.get(chunk_id, {})
        sources.append({
            "source_id": len(sources) + 1,
            "chunk_id": chunk_id,
            "anchor_id": c.get("anchor_id", ""),
            "section_number": c.get("section_number", ""),
            "section_title": c.get("section_title", ""),
            "heading_id": c.get("heading_id", ""),
            "document": c.get("document", ""),
            "pdf_page": pdf_map.get("page", 1),
            "pdf_bbox": pdf_map.get("bbox"),
            "pdf_query": make_pdf_search_query(pdf_map.get("match_text", "") or c.get("document", "")),
        })
    return sources


# ─────────────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are the Climate Academy Assistant — an educational chatbot built on the
Climate Academy Student Book by Matthew Pye (2025).

RULES (STRICTLY ENFORCE):
1. Answer ONLY from the numbered sources below. Do NOT use outside knowledge.
2. AUTOMATICALLY detect the user's language and reply in that same language.
3. You MAY combine information from multiple sources into one paragraph.
4. Every answer paragraph MUST include citations using source numbers.
5. Citations must reference only valid SOURCE_ID values from context.
6. If the answer is not in the sources, output one paragraph saying that and
   use an empty citations list.
7. Never invent facts.

OUTPUT FORMAT — respond with JSON object and nothing else:
{{
  "answer_blocks": [
    {{
      "text": "<single paragraph answer text>",
      "citations": [1, 2, 3]
    }}
  ]
}}

If you cannot produce valid JSON, output {{"answer_blocks": []}}.

--- RETRIEVED SOURCES ---
{context}
--- END OF SOURCES ---"""


# ─────────────────────────────────────────────────────
# GROQ
# ─────────────────────────────────────────────────────
def ask_groq(groq_client, chunks: list[dict], history: list, user_message: str, pdf_chunk_map: Optional[dict] = None) -> dict:
    """
    Calls Groq and returns:
      {
        "blocks": [{"text": str, "citations": [int, ...]}, ...],
        "sources": [{source metadata}, ...]
      }
    """
    sources = build_sources(chunks, pdf_chunk_map=pdf_chunk_map)
    context_parts = []
    for s in sources:
        passage = (
            f"[SOURCE_ID: {s['source_id']}] "
            f"[CHUNK_ID: {s['chunk_id']}] "
            f"[ANCHOR_ID: {s['anchor_id']}] "
            f"[§ {s['section_number']} — {s['section_title']}]\n"
            f"{s['document']}"
        )
        context_parts.append(passage)
    context = "\n\n---\n\n".join(context_parts)

    system   = SYSTEM_PROMPT.format(context=context)
    messages = [{"role": "system", "content": system}]
    for t in history[-8:]:
        if t["role"] in ("user", "assistant"):
            content = t.get("content") or ""
            if t["role"] == "assistant" and t.get("blocks"):
                content = " ".join(b.get("text", "") for b in t.get("blocks", []))
            messages.append({"role": t["role"], "content": content})
    messages.append({"role": "user", "content": user_message})

    try:
        resp = groq_client.chat.completions.create(
            model=GROQ_MODEL, messages=messages, max_tokens=2200, temperature=0.15,
        )
        raw = resp.choices[0].message.content.strip()

        # Strip possible markdown code fences
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("` \n")

        parsed = None
        try:
            parsed = json.loads(raw)
        except Exception:
            obj_match = re.search(r"\{[\s\S]*\}", raw)
            arr_match = re.search(r"\[[\s\S]*\]", raw)
            candidate = obj_match.group(0) if obj_match else (arr_match.group(0) if arr_match else "")
            if candidate:
                parsed = json.loads(candidate)
            else:
                parsed = {"answer_blocks": []}
        raw_blocks = []
        if isinstance(parsed, dict):
            raw_blocks = parsed.get("answer_blocks", [])
        elif isinstance(parsed, list):
            raw_blocks = parsed

        valid_source_ids = {s["source_id"] for s in sources}
        blocks = []
        for b in raw_blocks:
            text = str(b.get("text", "")).strip()
            if not text:
                continue
            citations = []
            for c in b.get("citations", []):
                if isinstance(c, int) and c in valid_source_ids and c not in citations:
                    citations.append(c)
            blocks.append({"text": text, "citations": citations})

        if not blocks:
            fallback_citations = [s["source_id"] for s in sources[:3]]
            blocks = [{
                "text": "I could not format a full structured answer this turn. Please retry this question.",
                "citations": fallback_citations,
            }]

        return {"blocks": blocks, "sources": sources}
    except Exception as e:
        err = str(e)
        if "rate_limit"      in err.lower():
            return {"blocks": [{"text": "Rate limit reached. Please wait a moment.", "citations": []}], "sources": sources}
        if "invalid_api_key" in err.lower():
            return {"blocks": [{"text": "Invalid GROQ_API_KEY.", "citations": []}], "sources": sources}
        return {"blocks": [{"text": f"{err[:200]}", "citations": []}], "sources": sources}


import re as _re  # make re available for ask_groq's strip logic
# Re-assign so ask_groq can use it
import re


# ─────────────────────────────────────────────────────
# BOOK VIEWER
# ─────────────────────────────────────────────────────
def render_book_viewer(
    book_html: str,
    target_anchor_id: Optional[str] = None,
    target_section:   Optional[str] = None,
    heading_id:        str = "",
    jump_type:         str = "section",  # "para" or "section"
    height:            int = BOOK_VIEWER_HEIGHT,
):
    """
    Renders the annotated book HTML.

    When jump_type == "para":
      fires  ca-jump-para  with anchor_id  →  highlights EXACT paragraph

    When jump_type == "section" (legacy):
      fires  ca-jump  with section number  →  highlights whole ca-section div
    """
    trigger = ""
    if jump_type == "para" and target_anchor_id:
        payload = json.dumps({
            "type":      "ca-jump-para",
            "anchor_id": target_anchor_id,
            "section":   target_section or "",
        })
        trigger = f"""
<script>
(function() {{
    function fire() {{
        window.dispatchEvent(new MessageEvent('message', {{ data: {payload} }}));
    }}
    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', fire);
    }} else {{
        fire();
    }}
}})();
</script>
"""
    elif jump_type == "section" and target_section:
        payload = json.dumps({
            "type":       "ca-jump",
            "section":    target_section,
            "keywords":   [],
            "heading_id": heading_id,
        })
        trigger = f"""
<script>
(function() {{
    function fire() {{
        window.dispatchEvent(new MessageEvent('message', {{ data: {payload} }}));
    }}
    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', fire);
    }} else {{
        fire();
    }}
}})();
</script>
"""

    final = book_html
    if trigger:
        if "</body>" in final:
            final = final.replace("</body>", trigger + "</body>")
        else:
            final += trigger

    components.html(final, height=height, scrolling=True)


@st.cache_data
def load_pdf_data_uri(pdf_path: str) -> str:
    raw = Path(pdf_path).read_bytes()
    b64 = base64.b64encode(raw).decode("utf-8")
    return f"data:application/pdf;base64,{b64}"


def make_pdf_search_query(text: str, max_words: int = 14) -> str:
    if not text:
        return ""
    cleaned = " ".join(text.replace("\n", " ").split())
    words = cleaned.split(" ")
    return " ".join(words[:max_words]).strip()


def _norm_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _keyword_set(text: str, max_words: int = 24) -> set[str]:
    words = [w for w in _norm_text(text).split(" ") if len(w) >= 5]
    return set(words[:max_words])


@st.cache_resource
def load_pdf_index(pdf_path: str) -> list[dict]:
    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc):
        blocks = []
        for b in page.get_text("blocks"):
            if len(b) < 5:
                continue
            x0, y0, x1, y1, text = b[:5]
            t = (text or "").strip()
            if len(t) < 25:
                continue
            blocks.append({
                "text": t,
                "norm": _norm_text(t),
                "bbox": [float(x0), float(y0), float(x1), float(y1)],
            })

        page_text = page.get_text("text") or ""
        pages.append({
            "page": i + 1,
            "norm": _norm_text(page_text),
            "blocks": blocks,
        })
    doc.close()
    return pages


def _best_page_and_block(chunk_text: str, pdf_index: list[dict]) -> dict:
    chunk_keywords = _keyword_set(chunk_text)
    chunk_norm = _norm_text(chunk_text)
    if not chunk_norm:
        return {"page": 1, "bbox": None, "match_text": ""}

    best_page = {"page": 1, "score": -1.0, "blocks": []}
    for p in pdf_index:
        page_norm = p["norm"]
        if not page_norm:
            continue
        if chunk_keywords:
            page_words = set(page_norm.split(" "))
            overlap = len(chunk_keywords.intersection(page_words))
            score = overlap / max(1, len(chunk_keywords))
        else:
            score = 0.0
        if score > best_page["score"]:
            best_page = {"page": p["page"], "score": score, "blocks": p["blocks"]}

    best_block = {"score": -1.0, "bbox": None, "text": ""}
    for b in best_page["blocks"]:
        block_norm = b["norm"]
        if not block_norm:
            continue
        if chunk_keywords:
            block_words = set(block_norm.split(" "))
            overlap = len(chunk_keywords.intersection(block_words))
            score = overlap / max(1, len(chunk_keywords))
        else:
            score = 0.0
        if score > best_block["score"]:
            best_block = {"score": score, "bbox": b["bbox"], "text": b["text"]}

    return {
        "page": int(best_page["page"]),
        "bbox": best_block["bbox"],
        "match_text": best_block["text"] or chunk_text,
    }


@st.cache_data
def map_chunks_to_pdf(chunks: list[dict], pdf_path: str) -> dict:
    if not Path(pdf_path).is_file():
        return {}
    pdf_index = load_pdf_index(pdf_path)
    mapped = {}
    for c in chunks:
        chunk_id = c.get("chunk_id", "")
        if not chunk_id:
            continue
        mapped[chunk_id] = _best_page_and_block(c.get("document", ""), pdf_index)
    return mapped


def render_pdf_viewer(
    pdf_data_uri: str,
    search_query: str = "",
    page_number: Optional[int] = None,
    height: int = BOOK_VIEWER_HEIGHT,
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


# ─────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────
def _welcome_message() -> str:
    return (
        "Hello! I'm the Climate Academy Assistant.\n\n"
        "Ask me anything about the book. Answers are combined into clear paragraphs, and each paragraph has numbered source chips. "
        "Click a chip (1, 2, 3...) to jump to that source in the book."
    )


def _new_chat_name() -> str:
    return f"New Chat {len(st.session_state.chat_order) + 1}"


def _create_chat() -> None:
    chat_id = f"chat_{uuid4().hex[:10]}"
    st.session_state.chats[chat_id] = {
        "name": _new_chat_name(),
        "messages": [{"role": "assistant", "content": _welcome_message(), "message_id": "welcome"}],
    }
    st.session_state.chat_order.insert(0, chat_id)
    st.session_state.current_chat_id = chat_id


def _chat_preview(chat_id: str) -> str:
    chat = st.session_state.chats.get(chat_id, {})
    for msg in chat.get("messages", []):
        if msg.get("role") == "user":
            text = (msg.get("content") or "").strip()
            if text:
                return (text[:34] + "...") if len(text) > 34 else text
    return chat.get("name", "New Chat")


def _init_session():
    defaults = {
        "chats":             {},
        "chat_order":        [],
        "current_chat_id":   None,
        "jump_anchor_id":    None,
        "jump_section":      None,
        "jump_heading_id":   "",
        "jump_type":         "section",
        "jump_pdf_query":    "",
        "jump_pdf_page":     1,
        "show_logs":         False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

    if not st.session_state.chat_order or not st.session_state.current_chat_id:
        _create_chat()

_init_session()


# ─────────────────────────────────────────────────────
# LOAD RESOURCES
# ─────────────────────────────────────────────────────
collection, embedder = build_knowledge_base()
groq_client          = load_groq()

ensure_html_media_assets(HTML_PATH, DOCX_PATH)

BOOK_HTML = (
    get_annotated_book_html(str(HTML_PATH))
    if HTML_PATH.is_file()
    else "<p style='color:red;padding:2rem'>⚠️ Book HTML not found. Check HTML_PATH in app.py.</p>"
)

BOOK_PDF_URI = load_pdf_data_uri(str(PDF_PATH)) if PDF_PATH.is_file() else ""


# ─────────────────────────────────────────────────────
# LAYOUT
# ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Chats")
    if st.button("➕ New Chat", use_container_width=True):
        _create_chat()
        st.rerun()

    for chat_id in st.session_state.chat_order:
        is_active = chat_id == st.session_state.current_chat_id
        prefix = "● " if is_active else ""
        label = prefix + _chat_preview(chat_id)
        if st.button(label, key=f"chat_pick_{chat_id}", use_container_width=True):
            st.session_state.current_chat_id = chat_id
            st.rerun()

    st.divider()
    if st.button("🧹 Clear Current Chat", use_container_width=True):
        current = st.session_state.chats[st.session_state.current_chat_id]
        current["messages"] = [{"role": "assistant", "content": _welcome_message(), "message_id": "welcome"}]
        st.session_state.jump_anchor_id = None
        st.session_state.jump_section = None
        st.session_state.jump_heading_id = ""
        st.session_state.jump_type = "section"
        st.session_state.jump_pdf_query = ""
        st.session_state.jump_pdf_page = 1
        st.rerun()

    if st.button("🗑️ Delete Current Chat", use_container_width=True):
        current_id = st.session_state.current_chat_id
        if len(st.session_state.chat_order) > 1:
            st.session_state.chat_order = [cid for cid in st.session_state.chat_order if cid != current_id]
            st.session_state.chats.pop(current_id, None)
            st.session_state.current_chat_id = st.session_state.chat_order[0]
        else:
            st.session_state.chats[current_id]["messages"] = [
                {"role": "assistant", "content": _welcome_message(), "message_id": "welcome"}
            ]
        st.session_state.jump_anchor_id = None
        st.session_state.jump_section = None
        st.session_state.jump_heading_id = ""
        st.session_state.jump_type = "section"
        st.session_state.jump_pdf_query = ""
        st.session_state.jump_pdf_page = 1
        st.rerun()

    st.divider()
    if st.button("📊 View Logs / Analytics", use_container_width=True):
        st.session_state.show_logs = not st.session_state.get("show_logs", False)
        st.rerun()


current_chat = st.session_state.chats[st.session_state.current_chat_id]
messages = current_chat["messages"]


if st.session_state.get("show_logs", False):
    st.markdown("## 📊 Chatbot Logs & Analytics")
    if st.button("⬅️ Back to Chat"):
        st.session_state.show_logs = False
        st.rerun()
    
    logs_data = get_all_logs()
    st.dataframe(logs_data, use_container_width=True)
    
    csv_str = get_logs_csv_string()
    if csv_str:
        st.download_button(
            "📥 Download as CSV",
            csv_str.encode('utf-8'),
            "chatbot_logs.csv",
            "text/csv",
            use_container_width=True
        )
    st.stop()

col_chat, col_book = st.columns([5, 7], gap="small")

# ── LEFT: Chat ────────────────────────────────────────
with col_chat:
    st.markdown("""
    <div class="panel-header">
        <p class="panel-title">🌍 Climate Academy Assistant</p>
        <p class="panel-subtitle">Ask a question and get grounded answers with paragraph-level sources.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<p class="section-label">Conversation</p>', unsafe_allow_html=True)

    message_count = len(messages)
    chat_history_height = max(360, min(680, 170 + (message_count * 105)))
    history_box = st.container(height=chat_history_height, border=False)
    with history_box:
        for msg_idx, msg in enumerate(messages):
            if msg["role"] == "assistant":
                blocks = msg.get("blocks") or []
                sources = msg.get("sources") or []
                source_by_id = {s.get("source_id"): s for s in sources}

                if blocks:
                    for bi, block in enumerate(blocks):
                        text = block.get("text", "")
                        citations = block.get("citations", [])

                        st.markdown(
                            f'<div class="point-card"><div class="point-body">{text}</div></div>',
                            unsafe_allow_html=True,
                        )

                        if citations:
                            chip_cols = st.columns(len(citations))
                            for ci, source_id in enumerate(citations):
                                source = source_by_id.get(source_id, {})
                                sec_num = source.get("section_number", "")
                                sec_title = source.get("section_title", "")
                                source_line = f"§ {sec_num}" if sec_num else "Source"
                                if sec_title:
                                    source_line += f" — {sec_title}"

                                key = f"cite_{st.session_state.current_chat_id}_{msg_idx}_{bi}_{source_id}"
                                if chip_cols[ci].button(
                                    str(source_id),
                                    key=key,
                                    help=f"Jump to source {source_id}\n{source_line}",
                                    use_container_width=True,
                                ):
                                    st.session_state.jump_anchor_id = source.get("anchor_id", "")
                                    st.session_state.jump_section = source.get("section_number", "")
                                    st.session_state.jump_heading_id = source.get("heading_id", "")
                                    st.session_state.jump_type = "para" if source.get("anchor_id") else "section"
                                    st.session_state.jump_pdf_query = source.get("pdf_query", "")
                                    st.session_state.jump_pdf_page = source.get("pdf_page", 1)
                                    st.rerun()
                else:
                    content = msg.get("content", "")
                    st.markdown(
                        f'<div class="msg-row-bot">'
                        f'<div class="avatar">CA</div>'
                        f'<div class="bubble-bot">{content.replace(chr(10), "<br>")}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                message_id = msg.get("message_id")
                if message_id and message_id != "welcome":
                    fb_col1, fb_col2, _ = st.columns([1, 1, 8])
                    if fb_col1.button("👍", key=f"up_{message_id}", help="Good response"):
                        update_feedback(message_id, 1)
                        st.toast("Thanks for your feedback! 👍")
                    if fb_col2.button("👎", key=f"down_{message_id}", help="Bad response"):
                        update_feedback(message_id, 0)
                        st.toast("Thanks for your feedback! 👎")
            else:
                content = msg.get("content", "")
                st.markdown(
                    f'<div class="msg-row-user">'
                    f'<div class="bubble-user">{content.replace(chr(10), "<br>")}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    user_input = st.chat_input("Ask about climate change...")
    if user_input:
        messages.append({"role": "user", "content": user_input})

        if current_chat["name"].startswith("New Chat"):
            current_chat["name"] = (user_input[:28] + "...") if len(user_input) > 28 else user_input

        with st.spinner("Thinking..."):
            chunks = retrieve(user_input, collection, embedder)
            pdf_chunk_map = map_chunks_to_pdf(chunks, str(PDF_PATH)) if PDF_PATH.is_file() else {}
            answer = ask_groq(groq_client, chunks, messages[:-1], user_input, pdf_chunk_map=pdf_chunk_map)

        blocks = answer.get("blocks", [])
        sources = answer.get("sources", [])
        first_source = None
        if blocks and blocks[0].get("citations"):
            first_source_id = blocks[0]["citations"][0]
            first_source = next((s for s in sources if s.get("source_id") == first_source_id), None)

        if first_source:
            st.session_state.jump_anchor_id = first_source.get("anchor_id", "")
            st.session_state.jump_section = first_source.get("section_number", "")
            st.session_state.jump_heading_id = first_source.get("heading_id", "")
            st.session_state.jump_type = "para" if first_source.get("anchor_id") else "section"
            st.session_state.jump_pdf_query = first_source.get("pdf_query", "")
            st.session_state.jump_pdf_page = first_source.get("pdf_page", 1)

        message_id = str(uuid4())
        messages.append({"role": "assistant", "content": None, "blocks": blocks, "sources": sources, "message_id": message_id})
        
        bot_resp_text = ""
        if blocks:
            bot_resp_text = "\n\n".join(b.get("text", "") for b in blocks)
        elif answer.get("blocks"):
            bot_resp_text = answer.get("blocks")[0].get("text", "")
            
        log_interaction(message_id, st.session_state.current_chat_id, user_input, bot_resp_text)

        st.rerun()

    st.divider()
    if st.button("📖 Reset Book View", use_container_width=True):
        st.session_state.jump_anchor_id = None
        st.session_state.jump_section = None
        st.session_state.jump_heading_id = ""
        st.session_state.jump_type = "section"
        st.session_state.jump_pdf_query = ""
        st.session_state.jump_pdf_page = 1
        st.rerun()

    st.markdown(
        f'<p class="disclaimer">'
        f'Answers based solely on the Climate Academy Student Book.<br>'
        f'Embeddings: {EMBED_MODEL} · LLM: {GROQ_MODEL}'
        f'</p>',
        unsafe_allow_html=True,
    )


# ── RIGHT: Book viewer ───────────────────────────────
with col_book:
    st.markdown("""
    <div class="panel-header">
        <p class="panel-title">📖 Climate Academy Student Book</p>
        <p class="panel-subtitle">Matthew Pye · 2025 · Click <b>View Source</b> on any answer card to jump to the exact paragraph.</p>
    </div>
    """, unsafe_allow_html=True)

    render_book_viewer(
        BOOK_HTML,
        target_anchor_id=st.session_state.jump_anchor_id,
        target_section=st.session_state.jump_section,
        heading_id=st.session_state.jump_heading_id,
        jump_type=st.session_state.jump_type,
        height=BOOK_VIEWER_HEIGHT,
    )

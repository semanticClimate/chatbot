"""
Author: Udita Agarwal 2026
Licence Apache 2.0

Climate Academy Chatbot — Streamlit + Groq API
===============================================
Stack:
  - UI              : Streamlit
  - Book source     : HTML (nested <section>, decimal § numbering)
  - Free embeddings : sentence-transformers (all-MiniLM-L6-v2) — 100% local
  - Vector database : ChromaDB (persistent on disk)
  - LLM             : Groq API (llama-3.3-70b) — FREE, no credit card needed

Get your free Groq key at: https://console.groq.com
Run: streamlit run app.py
"""

import os
from pathlib import Path

import chromadb
import streamlit as st
from groq import Groq
from sentence_transformers import SentenceTransformer

from html_sectioning import format_passage_for_prompt, parse_html_path_to_chunks

# ─────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).resolve().parent
HTML_PATH       = BASE_DIR / "ClimateAcademyBook.html"
CHROMA_DIR      = str(BASE_DIR / "chroma_db")
COLLECTION_NAME = "climate_academy_book_html"
CHUNK_SIZE      = 400
CHUNK_OVERLAP   = 60
TOP_K           = 5
EMBED_MODEL     = "all-MiniLM-L6-v2"
GROQ_MODEL      = "llama-3.3-70b-versatile"   # free, fast, multilingual

# ─────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────
st.set_page_config(page_title="Climate Academy Chatbot", page_icon="🌍", layout="centered")

st.markdown("""
<style>
.header { background: #1a5c38; color: white; padding: 16px 24px; border-radius: 12px; margin-bottom: 20px; }
.header h2 { margin: 0; font-size: 22px; }
.header p  { margin: 4px 0 0; font-size: 13px; opacity: 0.8; }
.bubble-bot  { background: #ffffff; color: #1a1a1a !important; border-radius: 18px 18px 18px 4px; padding: 12px 16px; margin: 6px 0; font-size: 15px; line-height: 1.6; max-width: 85%; border: 1px solid #dde8dd; }
.bubble-user { background: #1a5c38; color: #ffffff !important; border-radius: 18px 18px 4px 18px; padding: 12px 16px; margin: 6px 0 6px auto; font-size: 15px; line-height: 1.6; max-width: 85%; text-align: right; }
.msg-row-bot  { display: flex; align-items: flex-start; gap: 10px; margin: 8px 0; }
.msg-row-user { display: flex; justify-content: flex-end; margin: 8px 0; }
.avatar { width: 34px; height: 34px; border-radius: 50%; background: #1a5c38; color: white; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 700; flex-shrink: 0; }
.disclaimer { text-align: center; font-size: 11px; color: #888; margin-top: 8px; }
.bubble-bot * { color: #1a1a1a !important; }
.bubble-user * { color: #ffffff !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────
# CACHED RESOURCES
# ─────────────────────────────────────────────────────
@st.cache_resource
def load_embedder():
    """Free local embedding model — downloads once, runs locally forever."""
    return SentenceTransformer(EMBED_MODEL)


@st.cache_resource
def load_groq():
    """Set up Groq client using API key from secrets or environment."""
    api_key = os.environ.get("GROQ_API_KEY") or st.secrets.get("GROQ_API_KEY", "")
    if not api_key:
        st.error(
            "⚠️ GROQ_API_KEY not set.\n\n"
            "1. Go to https://console.groq.com\n"
            "2. Sign up free — no credit card needed\n"
            "3. Click API Keys → Create API Key\n"
            "4. Add it to .streamlit/secrets.toml:\n\n"
            "   GROQ_API_KEY = 'gsk_...your_key'"
        )
        st.stop()
    return Groq(api_key=api_key)


@st.cache_resource
def build_knowledge_base():
    """
    Full RAG pipeline — runs ONCE on first launch, loads from disk every restart.
    HTML (nested sections) → decimal § numbering → chunk → embed → store in ChromaDB
    """
    embedder   = load_embedder()
    chroma     = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = chroma.get_or_create_collection(
        name     = COLLECTION_NAME,
        metadata = {"hnsw:space": "cosine"}
    )

    # Already built — skip re-embedding
    if collection.count() > 0:
        return collection, embedder

    if not HTML_PATH.is_file():
        st.error(
            f"⚠️ HTML book not found at `{HTML_PATH}`.\n\n"
            "Add `ClimateAcademyBook.html` next to `app.py`, or update `HTML_PATH` in `app.py`."
        )
        st.stop()

    # ── Parse HTML → outline chunks ──────────────────────
    with st.spinner(f"📄 Parsing HTML book `{HTML_PATH.name}`..."):
        indexed = parse_html_path_to_chunks(HTML_PATH, CHUNK_SIZE, CHUNK_OVERLAP)
    if not indexed:
        st.error("No sections extracted from HTML — check structure in docs/HTML_SECTION_NESTING.md.")
        st.stop()

    # ── Embed + store in ChromaDB ──────────────────
    bar = st.progress(0, text="🔄 Building knowledge base (first run only — ~2 min)...")
    n = len(indexed)
    for i in range(0, n, 64):
        batch = indexed[i : i + 64]
        docs = [c.document for c in batch]
        collection.add(
            documents  = docs,
            embeddings = embedder.encode(docs, show_progress_bar=False).tolist(),
            ids        = [f"html_chunk_{i + j}" for j in range(len(batch))],
            metadatas  = [
                {
                    "section_number": c.section_number,
                    "section_title": c.section_title or "",
                    "chunk_index": str(c.chunk_index),
                }
                for c in batch
            ],
        )
        bar.progress(
            min(1.0, (i + 64) / n),
            text=f"🔄 Embedding... {min(100, int((i + 64) / n * 100))}%",
        )

    bar.empty()
    st.success(f"✅ Knowledge base ready — {collection.count():,} chunks indexed!")
    return collection, embedder


# ─────────────────────────────────────────────────────
# RETRIEVE — semantic search
# ─────────────────────────────────────────────────────
def retrieve(query: str, collection, embedder) -> list:
    """Embed the question and find the top_k most similar book chunks."""
    query_vector = embedder.encode([query])[0].tolist()
    results      = collection.query(
        query_embeddings = [query_vector],
        n_results        = TOP_K,
        include          = ["documents", "distances", "metadatas"],
    )
    docs   = results["documents"][0]
    dists  = results["distances"][0]
    metas  = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
    triples = list(zip(docs, dists, metas))
    filtered = [(doc, d, m) for doc, d, m in triples if d < 1.5]
    use = filtered if filtered else triples
    return [
        format_passage_for_prompt(
            m.get("section_number") or "",
            m.get("section_title") or "",
            doc,
        )
        for doc, _d, m in use
    ]


# ─────────────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are the Climate Academy Assistant — a friendly, educational chatbot \
built on the Climate Academy Student Book by Matthew Pye (2025).

Rules you MUST follow:
1. Answer ONLY using the context passages below. Do NOT use outside knowledge.
2. AUTOMATICALLY detect the user's language and ALWAYS reply in that EXACT same language \
   (English, Hindi, French, or any other language the user writes in).
3. If the answer is not found in the context, say: \
   "I couldn't find information about that in the Climate Academy book." — in the user's language.
4. Be concise, clear and encouraging. Use bullet points when listing multiple items.
5. Never invent facts or statistics not present in the context.
6. When you use facts from a passage, cite its **book section number** in-line using the form \
   **§ x.y.z** (and the short section title if helpful). Cite at least once per distinct section used.

--- RETRIEVED BOOK PASSAGES ---
{context}
--- END OF PASSAGES ---"""


# ─────────────────────────────────────────────────────
# CALL GROQ API
# ─────────────────────────────────────────────────────
def ask_groq(groq_client, context_chunks: list, history: list, user_message: str) -> str:
    """
    Call Groq API with retrieved context + conversation history.
    Groq uses the standard OpenAI message format: system / user / assistant roles.
    """
    context = "\n\n---\n\n".join(context_chunks)
    system  = SYSTEM_PROMPT.format(context=context)

    # Build messages: system prompt + last 10 turns + current message
    messages = [{"role": "system", "content": system}]
    for turn in history[-10:]:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": user_message})

    try:
        response = groq_client.chat.completions.create(
            model      = GROQ_MODEL,
            messages   = messages,
            max_tokens = 1000,
            temperature= 0.3    # low = more factual answers
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        err = str(e)
        if "rate_limit" in err.lower():
            return "⚠️ Rate limit reached (30 requests/min on free tier). Please wait a moment and try again."
        if "invalid_api_key" in err.lower():
            return "⚠️ Invalid GROQ_API_KEY. Please check your key at console.groq.com."
        return f"⚠️ Error: {err[:200]}"


# ─────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "language" not in st.session_state:
    st.session_state.language = "English"


# ─────────────────────────────────────────────────────
# LOAD RESOURCES
# ─────────────────────────────────────────────────────
collection, embedder = build_knowledge_base()
groq_client          = load_groq()


# ─────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────
st.markdown("""
<div class="header">
  <h2>🌍 Climate Academy Assistant</h2>
  <p>Powered by the Climate Academy Student Book · Matthew Pye (2025)</p>
</div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🌐 Language")
    lang = st.radio(
        "Language",
        ["English", "हिन्दी (Hindi)", "Français (French)"],
        label_visibility="collapsed"
    )
    st.session_state.language = lang

    st.markdown("---")
    st.markdown("### 💡 Try asking")
    suggestions = {
        "English"           : ["What causes climate change?", "What is the greenhouse effect?", "How can we reduce carbon emissions?", "What are renewable energy sources?"],
        "हिन्दी (Hindi)"    : ["जलवायु परिवर्तन के कारण क्या हैं?", "ग्रीनहाउस प्रभाव क्या है?", "कार्बन उत्सर्जन कैसे कम करें?"],
        "Français (French)" : ["Quelles sont les causes du changement climatique?", "Qu'est-ce que l'effet de serre?", "Comment réduire les émissions?"]
    }
    for s in suggestions.get(lang, suggestions["English"]):
        if st.button(s, use_container_width=True):
            st.session_state.pending_question = s

    st.markdown("---")
    st.markdown(f"""### ℹ️ About
- **LLM:** Llama 3.3 70B via Groq (free)
- **Embeddings:** {EMBED_MODEL} (local)
- **Vector DB:** ChromaDB
- **Chunks:** {collection.count():,}""")

    if st.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# ─────────────────────────────────────────────────────
# WELCOME MESSAGE
# ─────────────────────────────────────────────────────
if not st.session_state.messages:
    welcome = {
        "English"           : "Hello! I'm the Climate Academy Assistant 🌍\n\nAsk me anything about climate change, sustainability, or environmental science — I'll answer based on the Climate Academy Student Book.",
        "हिन्दी (Hindi)"    : "नमस्ते! मैं क्लाइमेट एकेडमी असिस्टेंट हूँ 🌍\n\nजलवायु परिवर्तन, स्थिरता या पर्यावरण विज्ञान के बारे में कुछ भी पूछें।",
        "Français (French)" : "Bonjour! Je suis l'assistant de la Climate Academy 🌍\n\nPosez-moi des questions sur le changement climatique, la durabilité ou les sciences de l'environnement."
    }
    st.session_state.messages.append({
        "role"   : "assistant",
        "content": welcome.get(lang, welcome["English"])
    })


# ─────────────────────────────────────────────────────
# RENDER MESSAGES
# ─────────────────────────────────────────────────────
for msg in st.session_state.messages:
    if msg["role"] == "assistant":
        st.markdown(
            f'<div class="msg-row-bot"><div class="avatar">CA</div>'
            f'<div class="bubble-bot">{msg["content"].replace(chr(10), "<br>")}</div></div>',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f'<div class="msg-row-user">'
            f'<div class="bubble-user">{msg["content"].replace(chr(10), "<br>")}</div></div>',
            unsafe_allow_html=True
        )


# ─────────────────────────────────────────────────────
# CHAT INPUT + RESPONSE
# ─────────────────────────────────────────────────────
user_input = st.session_state.pop("pending_question", None)
typed      = st.chat_input("Ask about climate change...")
if typed:
    user_input = typed

if user_input:
    # Show user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.markdown(
        f'<div class="msg-row-user">'
        f'<div class="bubble-user">{user_input}</div></div>',
        unsafe_allow_html=True
    )

    with st.spinner("Thinking..."):
        # 1. Semantic search — find relevant book chunks
        chunks = retrieve(user_input, collection, embedder)

        # 2. Add language hint if sidebar language selected
        lang_hint = {
            "हिन्दी (Hindi)"   : " (Please reply in Hindi)",
            "Français (French)": " (Please reply in French)"
        }.get(lang, "")

        # 3. Call Groq
        reply = ask_groq(
            groq_client,
            chunks,
            st.session_state.messages[:-1],
            user_input + lang_hint
        )

    # Show bot reply
    st.session_state.messages.append({"role": "assistant", "content": reply})
    st.markdown(
        f'<div class="msg-row-bot"><div class="avatar">CA</div>'
        f'<div class="bubble-bot">{reply.replace(chr(10), "<br>")}</div></div>',
        unsafe_allow_html=True
    )


# ─────────────────────────────────────────────────────
# DISCLAIMER
# ─────────────────────────────────────────────────────
st.markdown(
    '<p class="disclaimer">Answers are based solely on the Climate Academy Student Book.</p>',
    unsafe_allow_html=True
)
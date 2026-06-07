"""
FastAPI sidecar for RAG + Groq. Stateless per request; optional interaction logging.

Run from repo root:
  export GROQ_API_KEY=...
  uvicorn fastapi_app.main:app --host 0.0.0.0 --port 8800
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field, field_validator
from starlette.responses import HTMLResponse

from climate_streamlit.config_loader import AppSettings, get_settings
from climate_streamlit.db import get_logs_csv_string, log_interaction
from climate_streamlit.html_sectioning import load_html_file, parse_book_html
from climate_streamlit.llm.groq_client import load_groq_from_env
from climate_streamlit.rag.book_document import build_annotated_book_document
from climate_streamlit.rag.encyclopedia_document import (
    build_encyclopedia_entry_document,
    build_encyclopedia_placeholder_document,
    normalize_entry_id,
    prepared_encyclopedia_path,
)
from climate_streamlit.rag.indexing import build_knowledge_base_core
from climate_streamlit.services.chat_service import run_ask, run_retrieve
from climate_streamlit.services.conversation import (
    append_turn,
    conversation_from_csv,
    conversation_to_csv,
    normalize_conversation,
)

logger = logging.getLogger(__name__)

RESPONSE_LANGUAGE_CODES = frozenset({"en", "fr", "es", "pt", "hi"})


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    conversation: list[dict[str, Any]] = Field(default_factory=list)
    top_k: int | None = None
    chat_id: str | None = None
    message_id: str | None = None
    response_language: str = Field(default="en")

    @field_validator("response_language")
    @classmethod
    def _normalize_response_language(cls, v: str) -> str:
        code = (v or "en").strip().lower()
        if code not in RESPONSE_LANGUAGE_CODES:
            raise ValueError(
                "response_language must be one of: "
                + ", ".join(sorted(RESPONSE_LANGUAGE_CODES))
            )
        return code


class RetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int | None = None


class ConversationImportBody(BaseModel):
    messages: list[dict[str, Any]]


class ConversationExportBody(BaseModel):
    conversation: list[dict[str, Any]]
    format: str = "json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    app.state.settings = settings
    logger.info("Loading Chroma index from %s", settings.chroma_dir)
    collection, embedder = build_knowledge_base_core(
        settings,
        progress_callback=lambda f, t: logger.info("Indexing: %s", t),
    )
    app.state.collection = collection
    app.state.embedder = embedder
    logger.info("Groq client init")
    app.state.groq = load_groq_from_env()
    yield


def _cors_origins() -> list[str]:
    raw = os.environ.get("CLIMATE_API_CORS_ORIGINS", "*").strip()
    if raw == "*":
        return ["*"]
    return [p.strip() for p in raw.split(",") if p.strip()]


app = FastAPI(title="Climate Academy RAG API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
def root() -> HTMLResponse:
    """Help people who open the API tunnel URL in a browser by mistake."""
    return HTMLResponse(
        content="""<!doctype html>
<meta charset="utf-8">
<title>Climate Academy API</title>
<h1>Climate Academy API</h1>
<p>This host is the <strong>API server</strong>, not the chat page in your browser.</p>
<p>Open the <strong>web client</strong> URL you were given (another
<code>*.trycloudflare.com</code> hostname) to use the chat UI.</p>
<p>Checks: <a href="/health">/health</a> · <a href="/ready">/ready</a></p>
""",
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/logs/export")
def logs_export_csv() -> Response:
    """SQLite-backed interaction logs as CSV (same data as Streamlit analytics download)."""
    csv_str = get_logs_csv_string()
    if not csv_str.strip():
        csv_str = "id,timestamp,chat_id,user_query,bot_response,feedback\n"
    return Response(
        content=csv_str.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="chatbot_logs.csv"'},
    )


@app.get("/ready")
def ready(request: Request) -> dict[str, Any]:
    s: AppSettings = request.app.state.settings
    col = request.app.state.collection
    html_ok = s.html_path.is_file()
    try:
        n = col.count()
    except Exception:
        n = 0
    return {
        "ready": bool(html_ok and n > 0),
        "chunk_count": n,
        "html_exists": html_ok,
    }


def _cached_book_outline(app: FastAPI) -> list[dict[str, Any]]:
    if getattr(app.state, "_book_outline_rows", None) is None:
        s: AppSettings = app.state.settings
        raw = load_html_file(s.html_path)
        records = parse_book_html(raw)
        app.state._book_outline_rows = [
            {
                "section_number": r.section_number,
                "title": r.title,
                "heading_id": r.heading_id,
                "level": r.level,
            }
            for r in records
        ]
    return app.state._book_outline_rows


def _cached_book_html(app: FastAPI) -> str:
    if getattr(app.state, "_book_document_html", None) is None:
        app.state._book_document_html = build_annotated_book_document(app.state.settings)
    return app.state._book_document_html


@app.get("/book/outline")
def book_outline(request: Request) -> dict[str, Any]:
    """Decimal outline (§ / title) for the student book — same structure Streamlit uses for navigation."""
    s: AppSettings = request.app.state.settings
    if not s.html_path.is_file():
        raise HTTPException(status_code=503, detail="Book HTML not available")
    return {"sections": _cached_book_outline(request.app)}


@app.get("/book/document", response_class=HTMLResponse)
def book_document(request: Request) -> HTMLResponse:
    """Annotated book HTML for embedding in the browser client iframe."""
    s: AppSettings = request.app.state.settings
    if not s.html_path.is_file():
        raise HTTPException(status_code=503, detail="Book HTML not available")
    return HTMLResponse(content=_cached_book_html(request.app))


def _cached_encyclopedia_placeholder(app: FastAPI) -> str:
    if getattr(app.state, "_encyclopedia_placeholder_html", None) is None:
        app.state._encyclopedia_placeholder_html = build_encyclopedia_placeholder_document()
    return app.state._encyclopedia_placeholder_html


@app.get("/encyclopedia/empty", response_class=HTMLResponse)
def encyclopedia_empty(request: Request) -> HTMLResponse:
    """Placeholder document for the encyclopedia iframe before a term is chosen."""
    return HTMLResponse(content=_cached_encyclopedia_placeholder(request.app))


@app.get("/encyclopedia/entry/{entry_id}", response_class=HTMLResponse)
def encyclopedia_entry(entry_id: str, request: Request) -> HTMLResponse:
    """Single CA encyclopedia entry for the browser client iframe."""
    s: AppSettings = request.app.state.settings
    enc = prepared_encyclopedia_path(s)
    if not enc.is_file():
        raise HTTPException(status_code=503, detail="Encyclopedia HTML not available")
    try:
        wid = normalize_entry_id(entry_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    try:
        html = build_encyclopedia_entry_document(wid, s)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return HTMLResponse(content=html)


@app.get("/proxy", response_class=HTMLResponse)
async def proxy_external(url: str, request: Request) -> HTMLResponse:
    """Proxy external Wikipedia/Wikidata requests to bypass iframe restrictions."""
    import httpx
    from urllib.parse import urlparse
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if not ("wikipedia.org" in domain or "wikidata.org" in domain):
        raise HTTPException(status_code=400, detail="Only Wikipedia and Wikidata links can be proxied.")
    
    try:
        async with httpx.AsyncClient() as client:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            response = await client.get(url, headers=headers, follow_redirects=True)
            content = response.text
            
            # Insert a base tag so relative assets resolve to the original site
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            base_tag = f'\n<base href="{base_url}/">\n'
            if "<head>" in content:
                content = content.replace("<head>", f"<head>{base_tag}", 1)
            elif "<HEAD>" in content:
                content = content.replace("<HEAD>", f"<HEAD>{base_tag}", 1)
            else:
                content = f"{base_tag}{content}"
            
            # Inject link interception script inside the proxied page to rewrite sub-links
            script_tag = """
<script>
(function() {
  document.addEventListener("click", function(e) {
    var anchor = e.target.closest("a");
    if (!anchor) return;
    var href = anchor.getAttribute("href");
    if (!href) return;
    var absoluteUrl = new URL(href, document.baseURI).href;
    if (absoluteUrl.indexOf("wikipedia.org") >= 0 || absoluteUrl.indexOf("wikidata.org") >= 0) {
      e.preventDefault();
      window.location.href = "/proxy?url=" + encodeURIComponent(absoluteUrl);
    }
  });
})();
</script>
"""
            if "</body>" in content:
                content = content.replace("</body>", f"{script_tag}</body>", 1)
            elif "</BODY>" in content:
                content = content.replace("</BODY>", f"{script_tag}</BODY>", 1)
            else:
                content = f"{content}{script_tag}"
                
            return HTMLResponse(content=content, status_code=response.status_code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch external resource: {str(e)}")



@app.post("/retrieve")
def retrieve_ep(request: Request, body: RetrieveRequest) -> dict[str, Any]:
    if body.top_k is not None and (body.top_k < 1 or body.top_k > 100):
        raise HTTPException(status_code=400, detail="top_k must be between 1 and 100")
    s: AppSettings = request.app.state.settings
    chunks = run_retrieve(
        body.query,
        request.app.state.collection,
        request.app.state.embedder,
        s,
        top_k=body.top_k,
    )
    return {"chunks": chunks}


@app.post("/ask")
def ask_ep(request: Request, body: AskRequest) -> dict[str, Any]:
    s: AppSettings = request.app.state.settings
    tk = body.top_k
    if tk is not None and (tk < 1 or tk > 100):
        raise HTTPException(status_code=400, detail="top_k must be between 1 and 100")

    conv = normalize_conversation(body.conversation)
    result = run_ask(
        body.question,
        conv,
        request.app.state.collection,
        request.app.state.embedder,
        request.app.state.groq,
        s,
        top_k=body.top_k,
        response_language=body.response_language,
    )
    updated = append_turn(
        conv,
        user_text=body.question,
        assistant_blocks=result["blocks"],
        assistant_sources=result["sources"],
        operator_detail=result.get("operator_detail"),
    )
    start = len(conv)
    out = {
        "blocks": result["blocks"],
        "sources": result["sources"],
        "operator_detail": result.get("operator_detail"),
        "timings_ms": result["timings_ms"],
        "conversation_append": updated[start:],
        "conversation_full": updated,
    }

    if body.message_id and body.chat_id:
        bot_text = "\n\n".join(b.get("text", "") for b in result.get("blocks", []))
        try:
            log_interaction(body.message_id, body.chat_id, body.question, bot_text)
        except Exception as e:
            logger.warning("log_interaction failed: %s", e)

    return out


@app.get("/book/jump")
def book_jump(
    anchor_id: str | None = None,
    section_number: str | None = None,
    heading_id: str | None = None,
) -> dict[str, Any]:
    jump_type = "para" if anchor_id else "section"
    return {
        "anchor_id": anchor_id,
        "section_number": section_number,
        "heading_id": heading_id or "",
        "jump_type": jump_type,
    }


@app.post("/conversation/import")
def conversation_import_ep(body: ConversationImportBody) -> dict[str, Any]:
    return {"conversation": normalize_conversation(body.messages)}


@app.post("/conversation/import_csv")
async def conversation_import_csv(request: Request) -> dict[str, Any]:
    raw = (await request.body()).decode("utf-8", errors="replace")
    conv = normalize_conversation(conversation_from_csv(raw))
    return {"conversation": conv}


@app.post("/conversation/export")
def conversation_export_ep(body: ConversationExportBody) -> Response:
    fmt = (body.format or "json").lower().strip()
    norm = normalize_conversation(body.conversation)
    if fmt == "csv":
        csv_text = conversation_to_csv(norm)
        return Response(
            content=csv_text.encode("utf-8"),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="conversation.csv"'},
        )
    if fmt == "json":
        return JSONResponse({"conversation": norm})
    raise HTTPException(status_code=400, detail="format must be json or csv")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("CLIMATE_API_PORT", "8800"))
    uvicorn.run(
        "fastapi_app.main:app",
        host=os.environ.get("CLIMATE_API_HOST", "0.0.0.0"),
        port=port,
        reload=False,
    )

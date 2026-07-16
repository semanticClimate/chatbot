from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config.settings import AppSettings, get_settings
from backend.app.llm.groq_client import load_groq_from_env
from backend.app.rag.indexing import build_knowledge_base_core
from backend.app.api.ask import router as ask_router

from backend.app.api.routes.chat import router as chat_router
from backend.app.api.routes.chat import router as chat_router
from backend.app.api.routes.books import router as books_router
from backend.app.api.routes.encyclopedia import router as encyclopedia_router
from backend.app.api.routes.conversation import router as conversation_router
from backend.app.api.routes.health import router as health_router
from pathlib import Path
from fastapi.staticfiles import StaticFiles
PROJECT_ROOT = Path(__file__).resolve().parents[2]

MEDIA_DIR = PROJECT_ROOT / "data" / "input" / "media"
logger = logging.getLogger(__name__)




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


app = FastAPI(
    title="Climate Academy RAG API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.mount(
    "/book/media",
    StaticFiles(directory=MEDIA_DIR),
    name="book_media",
)

app.include_router(health_router)
app.include_router(chat_router)
app.include_router(books_router)
app.include_router(encyclopedia_router)
app.include_router(conversation_router)

app.include_router(ask_router)

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("CLIMATE_API_PORT", "8800"))

    uvicorn.run(
        "fastapi_app.main:app",
        host=os.environ.get("CLIMATE_API_HOST", "0.0.0.0"),
        port=port,
        reload=False,
    )

from typing import Any

from fastapi import APIRouter,FastAPI, HTTPException, Request
from starlette.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator
from backend.app.config.settings import AppSettings
from backend.app.services.chat_service import run_ask, run_retrieve
from backend.app.services.conversation import (
    append_turn,
    conversation_from_csv,
    conversation_to_csv,
    normalize_conversation,
)
from backend.app.database.db import get_logs_csv_string, log_interaction

from backend.app.utils.html_sectioning import (
    load_html_file,
    parse_book_html,
)

from backend.app.rag.book_document import (
    build_annotated_book_document,
)

import logging
logger = logging.getLogger(__name__)



RESPONSE_LANGUAGE_CODES = frozenset({"en", "fr", "es", "pt", "hi"})

router = APIRouter()


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

@router.post("/ask")
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
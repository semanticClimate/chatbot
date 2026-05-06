"""HTTP client for the optional FastAPI RAG sidecar (`api_server.py`)."""

from __future__ import annotations

import os
from typing import Any, Optional


def get_api_base_url() -> str:
    return os.environ.get("CLIMATE_API_BASE_URL", "").strip().rstrip("/")


def messages_to_api_conversation(messages: list[dict]) -> list[dict[str, Any]]:
    """Shape Streamlit chat messages for POST /ask `conversation` field."""
    conv: list[dict[str, Any]] = []
    for m in messages:
        if m.get("role") == "assistant":
            entry: dict[str, Any] = {"role": "assistant", "content": m.get("content")}
            if m.get("blocks"):
                entry["blocks"] = m["blocks"]
            conv.append(entry)
        elif m.get("role") == "user":
            conv.append({"role": "user", "content": m.get("content", "")})
    return conv


def ask_via_api(
    base_url: str,
    question: str,
    conversation: list[dict[str, Any]],
    *,
    top_k: Optional[int] = None,
    chat_id: Optional[str] = None,
    message_id: Optional[str] = None,
    timeout_s: float = 180.0,
) -> dict[str, Any]:
    import httpx

    base = base_url.rstrip("/")
    payload: dict[str, Any] = {
        "question": question,
        "conversation": conversation,
    }
    if top_k is not None:
        payload["top_k"] = top_k
    if chat_id:
        payload["chat_id"] = chat_id
    if message_id:
        payload["message_id"] = message_id

    with httpx.Client(timeout=timeout_s) as client:
        r = client.post(f"{base}/ask", json=payload)
        r.raise_for_status()
        return r.json()

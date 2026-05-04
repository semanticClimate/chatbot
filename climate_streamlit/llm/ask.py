"""Groq chat completion with RAG context."""

from __future__ import annotations

from typing import Optional

from config_loader import AppSettings
from llm.parsing import (
    message_when_no_answer_blocks,
    normalize_answer_blocks,
    operator_detail_no_blocks,
    parse_llm_json_blob,
)
from llm.prompts import load_system_prompt_template
from rag.sources import build_sources


def ask_groq(
    groq_client,
    chunks: list[dict],
    history: list,
    user_message: str,
    settings: AppSettings,
    pdf_chunk_map: Optional[dict] = None,
) -> dict:
    """
    Calls Groq and returns:
      {
        "blocks": [{"text": str, "citations": [int, ...]}, ...],
        "sources": [{source metadata}, ...],
        "operator_detail": optional str (technical diagnostics for operators),
      }
    """
    sources = build_sources(chunks, settings, pdf_chunk_map=pdf_chunk_map)
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

    template = load_system_prompt_template(settings.base_dir)
    system = template.format(context=context)
    messages = [{"role": "system", "content": system}]
    for t in history[-settings.llm_history_turns :]:
        if t["role"] in ("user", "assistant"):
            content = t.get("content") or ""
            if t["role"] == "assistant" and t.get("blocks"):
                content = " ".join(b.get("text", "") for b in t.get("blocks", []))
            messages.append({"role": t["role"], "content": content})
    messages.append({"role": "user", "content": user_message})

    try:
        resp = groq_client.chat.completions.create(
            model=settings.groq_model,
            messages=messages,
            max_tokens=settings.llm_max_tokens,
            temperature=settings.llm_temperature,
        )
        choice = resp.choices[0]
        finish_reason = getattr(choice, "finish_reason", None)
        raw = (choice.message.content or "").strip()
        parsed = parse_llm_json_blob(raw)
        valid_source_ids = {s["source_id"] for s in sources}
        blocks = normalize_answer_blocks(parsed, valid_source_ids)

        operator_detail = None
        if not blocks:
            fallback_citations = [s["source_id"] for s in sources[:3]]
            blocks = [{
                "text": message_when_no_answer_blocks(raw, parsed, finish_reason),
                "citations": fallback_citations,
            }]
            operator_detail = operator_detail_no_blocks(
                raw, parsed, finish_reason, source_count=len(sources),
            )

        return {"blocks": blocks, "sources": sources, "operator_detail": operator_detail}
    except Exception as e:
        err = str(e)
        op_detail = f"exception_type={type(e).__name__}\nexception_message={err}"
        if "rate_limit" in err.lower():
            return {
                "blocks": [{"text": "You've hit a temporary usage limit. Wait a minute and try again.", "citations": []}],
                "sources": sources,
                "operator_detail": op_detail,
            }
        if "invalid_api_key" in err.lower():
            return {
                "blocks": [{"text": "This app can't reach the assistant because the API key is wrong or missing. Whoever set up the app needs to fix the key in secrets or environment.", "citations": []}],
                "sources": sources,
                "operator_detail": op_detail,
            }
        return {
            "blocks": [{"text": "Something went wrong while getting an answer from the assistant. Please try again in a moment.", "citations": []}],
            "sources": sources,
            "operator_detail": op_detail,
        }

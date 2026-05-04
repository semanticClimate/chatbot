"""Parse and normalize Groq JSON answer payloads."""

from __future__ import annotations

import html
import json
import re
from typing import Optional

_MAX_PLAIN_FALLBACK_CHARS = 12000


def _looks_like_inline_citation_number_list(obj: object) -> bool:
    """True for JSON like [1, 2, 3] — often appears in prose before the real structured JSON."""
    if not isinstance(obj, list) or not obj:
        return False
    for x in obj:
        if isinstance(x, bool):
            return False
        if isinstance(x, int):
            continue
        if isinstance(x, float) and x == int(x):
            continue
        return False
    return True


def parse_llm_json_blob(raw: str) -> dict | list | None:
    """
    Parse JSON from model output, which may include prose, ``` fences, and multiple
    JSON fragments. Prose citations like [1, 2, 3, 14] must NOT win over the
    trailing {\"answer_blocks\": [...]} object.
    """
    text = (raw or "").strip()
    if not text:
        return None
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*\s*\n?", "", text)
        text = re.sub(r"\s*```\s*$", "", text).strip()

    decoder = json.JSONDecoder()
    candidates: list[object] = []
    for i, ch in enumerate(text):
        if ch not in "{[":
            continue
        try:
            obj, _end = decoder.raw_decode(text, i)
            candidates.append(obj)
        except json.JSONDecodeError:
            continue
    if not candidates:
        return None

    answer_keys = ("answer_blocks", "blocks", "answers", "paragraphs")
    for obj in candidates:
        if isinstance(obj, dict) and any(k in obj for k in answer_keys):
            return obj

    for obj in candidates:
        if isinstance(obj, dict):
            return obj

    for obj in candidates:
        if (
            isinstance(obj, list)
            and obj
            and isinstance(obj[0], dict)
            and any(
                isinstance(obj[0].get(k), str)
                for k in ("text", "content", "body", "message", "answer")
            )
        ):
            return obj

    for obj in candidates:
        if _looks_like_inline_citation_number_list(obj):
            continue
        return obj

    return None


def fallback_plain_text_when_json_unparsed(raw: str) -> Optional[str]:
    """
    When the model did not produce parseable JSON but returned explanatory prose
    (common for unknown terms or “not in the book” replies), surface that text.

    If the output looks like a pure JSON attempt (starts with '{' and names answer_blocks),
    return None so the generic format message applies instead.
    """
    t = (raw or "").strip()
    if len(t) < 12:
        return None

    try:
        only = json.loads(t)
        if _looks_like_inline_citation_number_list(only):
            return None
    except (json.JSONDecodeError, TypeError, ValueError):
        pass

    t_low = t.lstrip()
    if t_low.startswith("{") and "answer_blocks" in t:
        return None

    if "{" not in t and "[" not in t:
        if len(t) > _MAX_PLAIN_FALLBACK_CHARS:
            return t[:_MAX_PLAIN_FALLBACK_CHARS] + "\n…"
        return t

    first_brace = t.find("{")
    if first_brace > 0:
        prefix = t[:first_brace].strip()
        if len(prefix) >= 24:
            if len(prefix) > _MAX_PLAIN_FALLBACK_CHARS:
                return prefix[:_MAX_PLAIN_FALLBACK_CHARS] + "\n…"
            return prefix

    return None


def escape_model_text_for_point_card(text: str) -> str:
    """Safe for insertion into HTML point-card body."""
    return html.escape(text, quote=False).replace("\n", "<br>")


def coerce_source_id(citation: object, valid_ids: set[int]) -> int | None:
    """Map model citation values to a valid SOURCE_ID."""
    if isinstance(citation, bool):
        return None
    if isinstance(citation, int):
        return citation if citation in valid_ids else None
    if isinstance(citation, float) and citation.is_integer():
        ic = int(citation)
        return ic if ic in valid_ids else None
    if isinstance(citation, str):
        s = citation.strip().lstrip("[").rstrip("]")
        if s.isdigit():
            ic = int(s)
            return ic if ic in valid_ids else None
    return None


def normalize_answer_blocks(
    parsed: dict | list | None,
    valid_source_ids: set[int],
) -> list[dict]:
    """
    Build [{text, citations}, ...] from varied LLM JSON shapes.
    """
    if not parsed:
        return []

    raw_blocks: list = []
    if isinstance(parsed, list):
        raw_blocks = parsed
    elif isinstance(parsed, dict):
        for key in (
            "answer_blocks", "blocks", "answers", "paragraphs",
            "data", "results", "response",
        ):
            val = parsed.get(key)
            if isinstance(val, list) and val:
                raw_blocks = val
                break
        if not raw_blocks:
            for k in ("text", "answer", "content", "message"):
                v = parsed.get(k)
                if isinstance(v, str) and v.strip():
                    cites = parsed.get("citations", parsed.get("sources", []))
                    if not isinstance(cites, list):
                        cites = []
                    raw_blocks = [{"text": v.strip(), "citations": cites}]
                    break

    out: list[dict] = []
    for b in raw_blocks:
        if isinstance(b, str) and b.strip():
            out.append({"text": b.strip(), "citations": []})
            continue
        if not isinstance(b, dict):
            continue

        text_piece = ""
        for tk in ("text", "content", "body", "message", "answer", "paragraph"):
            v = b.get(tk)
            if isinstance(v, str) and v.strip():
                text_piece = v.strip()
                break
        if not text_piece:
            continue

        cites_raw = (
            b.get("citations") or b.get("sources") or b.get("refs") or b.get("source_ids") or []
        )
        if isinstance(cites_raw, (int, float, str)):
            cites_raw = [cites_raw]
        if not isinstance(cites_raw, list):
            cites_raw = []

        citations: list[int] = []
        for c in cites_raw:
            sid = coerce_source_id(c, valid_source_ids)
            if sid is not None and sid not in citations:
                citations.append(sid)

        out.append({"text": text_piece, "citations": citations})

    return out


def message_when_no_answer_blocks(
    raw: str,
    parsed: dict | list | None,
    finish_reason: Optional[str],
) -> str:
    """
    Explain why we're showing a fallback reply, without technical jargon.
    """
    text = (raw or "").strip()
    fr = (finish_reason or "").strip().lower()

    if not text:
        return (
            "The assistant didn't return any text—only an empty reply. "
            "Try asking again, or shorten your question if it was very long."
        )

    if fr == "length":
        return (
            "The answer was longer than allowed in one step, so it was cut off and couldn't be displayed properly. "
            "Try asking a narrower question, or split it into smaller questions."
        )

    if parsed is None:
        return (
            "The assistant's reply wasn't in the format this app expects, so nothing could be shown. "
            "Try asking again, or ask in a simpler way."
        )

    return (
        "The assistant replied, but none of its paragraphs contained readable answer text "
        "(for example empty sections or placeholders). Try asking again, or break the question into parts."
    )


def operator_detail_no_blocks(
    raw: str,
    parsed: dict | list | None,
    finish_reason: Optional[str],
    *,
    source_count: int,
    extra_lines: tuple[str, ...] = (),
) -> str:
    """Technical summary for operators when normalization yields no paragraphs."""
    lines = [
        "event=no_paragraphs_after_normalize",
        f"finish_reason={finish_reason!r}",
        f"retrieved_source_count={source_count}",
        f"raw_model_output_chars={len((raw or '').strip())}",
    ]
    if parsed is None:
        lines.append("first_json_parse=failed_or_empty")
    elif isinstance(parsed, dict):
        keys = list(parsed.keys())
        lines.append(f"parsed_top_level=dict keys={keys!r}")
    elif isinstance(parsed, list):
        lines.append(f"parsed_top_level=list len={len(parsed)}")
    else:
        lines.append(f"parsed_top_level=unexpected {type(parsed).__name__}")

    lines.extend(extra_lines)

    snippet = (raw or "")[:2000]
    if len(raw or "") > 2000:
        snippet += "\n... [snippet truncated at 2000 chars for dashboard]"
    lines.append("")
    lines.append("--- raw model output (operator preview) ---")
    lines.append(snippet if snippet.strip() else "∅")
    return "\n".join(lines)

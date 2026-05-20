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

    answer_keys = ("answer_blocks", "blocks", "answers", "paragraphs")
    if candidates:
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

    loose = _try_relaxed_outer_json_parse(text)
    if isinstance(loose, dict):
        return loose
    if isinstance(loose, list) and loose and isinstance(loose[0], dict):
        if _looks_like_inline_citation_number_list(loose):
            return None
        return loose

    return None


def _strip_json_trailing_commas(s: str) -> str:
    """Remove lone trailing commas before } or ] (common malformed model JSON)."""
    s = re.sub(r",(\s*})", r"\1", s)
    s = re.sub(r",(\s*\])", r"\1", s)
    return s


def _try_relaxed_outer_json_parse(text: str) -> dict | list | None:
    """
    Last-resort JSON parse: take substring from first '{' through last '}' and
    load with trivial repairs. Helps when prose/extra fences break raw_decode scans.
    """
    t = (text or "").strip()
    fb = t.find("{")
    if fb == -1:
        return None
    lb = t.rfind("}")
    if lb <= fb:
        return None
    chunk = t[fb : lb + 1]
    variants = [chunk, _strip_json_trailing_commas(chunk)]
    for cand in variants:
        try:
            out = json.loads(cand)
        except json.JSONDecodeError:
            continue
        if isinstance(out, (dict, list)):
            return out
    return None


def consume_json_string_value(full: str, open_quote_idx: int) -> tuple[str, int | None]:
    """
    Read a JSON string literal starting at open_quote_idx (the opening double quote).
    Returns (decoded_utf8_content, idx_after_closing_quote) or (decoded, None) if truncated.
    """
    if open_quote_idx >= len(full) or full[open_quote_idx] != '"':
        return "", None
    i = open_quote_idx + 1
    out_chars: list[str] = []
    while i < len(full):
        c = full[i]
        if c != "\\":
            if c == '"':
                return "".join(out_chars), i + 1
            out_chars.append(c)
            i += 1
            continue
        i += 1
        if i >= len(full):
            out_chars.append("\\")
            break
        ec = full[i]
        if ec == '"':
            out_chars.append('"')
        elif ec == "\\":
            out_chars.append("\\")
        elif ec == "/":
            out_chars.append("/")
        elif ec == "b":
            out_chars.append("\b")
        elif ec == "f":
            out_chars.append("\f")
        elif ec == "n":
            out_chars.append("\n")
        elif ec == "r":
            out_chars.append("\r")
        elif ec == "t":
            out_chars.append("\t")
        elif ec == "u":
            hx = full[i + 1 : i + 5]
            if len(hx) == 4:
                try:
                    out_chars.append(chr(int(hx, 16)))
                    i += 5
                    continue
                except ValueError:
                    out_chars.append("u")
                    i += 1
                    continue
            out_chars.append("u")
            i += 1
            continue
        else:
            out_chars.append(ec)
        i += 1
    return "".join(out_chars), None


_TEXT_FIELD_PATTERN = re.compile(r'"text"\s*:\s*"')


def salvage_answer_blocks_from_near_json(raw: str) -> list[dict]:
    """
    Pull paragraph strings from malformed output that looks like answer_blocks JSON
    (e.g. truncated mid-response or stray characters outside an otherwise valid blob).
    """
    r = raw or ""
    if len(r.strip()) < 16:
        return []
    lowered = r.lower()
    if "answer_blocks" not in lowered and '"blocks"' not in lowered and '"text"' not in lowered:
        return []

    out: list[dict] = []
    for m in _TEXT_FIELD_PATTERN.finditer(r):
        oq = m.end() - 1  # opening " of JSON string value
        if oq < 0 or r[oq] != '"':
            continue
        body, _after = consume_json_string_value(r, oq)
        body = body.strip()
        if body:
            out.append({"text": body, "citations": []})

    merged: list[dict] = []
    for b in out:
        if merged and merged[-1]["text"] == b["text"]:
            continue
        merged.append(b)
    return merged


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

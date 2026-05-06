"""Normalize chat messages for REST request/response and file export."""

from __future__ import annotations

import csv
import io
import json
from typing import Any


def normalize_conversation(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Ensure each entry has role and content; assistant entries may include blocks.
    Unknown roles are skipped.
    """
    out: list[dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        if role not in ("user", "assistant"):
            continue
        entry: dict[str, Any] = {"role": role}
        if role == "user":
            entry["content"] = str(m.get("content", ""))
        else:
            entry["content"] = m.get("content")
            if m.get("blocks"):
                entry["blocks"] = m["blocks"]
            if m.get("operator_detail"):
                entry["operator_detail"] = m["operator_detail"]
        out.append(entry)
    return out


def append_turn(
    conversation: list[dict[str, Any]],
    *,
    user_text: str,
    assistant_blocks: list[dict[str, Any]],
    assistant_sources: list[dict[str, Any]],
    operator_detail: str | None = None,
) -> list[dict[str, Any]]:
    """Return a new conversation list with user + assistant turns appended."""
    next_conv = list(conversation)
    next_conv.append({"role": "user", "content": user_text})
    asst: dict[str, Any] = {
        "role": "assistant",
        "content": None,
        "blocks": assistant_blocks,
        "sources": assistant_sources,
    }
    if operator_detail:
        asst["operator_detail"] = operator_detail
    next_conv.append(asst)
    return next_conv


def conversation_to_csv(messages: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["role", "content"])
    for m in messages:
        role = m.get("role", "")
        if m.get("role") == "assistant" and m.get("blocks"):
            content = "\n\n".join(str(b.get("text", "")) for b in m.get("blocks", []))
        else:
            content = str(m.get("content", ""))
        writer.writerow([role, content])
    return buf.getvalue()


def conversation_from_csv(text: str) -> list[dict[str, Any]]:
    buf = io.StringIO(text)
    reader = csv.DictReader(buf)
    out: list[dict[str, Any]] = []
    for row in reader:
        role = (row.get("role") or "").strip()
        content = row.get("content") or ""
        if role == "user":
            out.append({"role": "user", "content": content})
        elif role == "assistant":
            out.append({"role": "assistant", "content": content})
    return normalize_conversation(out)


def conversation_to_json_bytes(messages: list[dict[str, Any]]) -> bytes:
    return json.dumps(messages, ensure_ascii=False, indent=2).encode("utf-8")

"""
Local daily Zoom transcript anonymization + summarization.

Input: meeting_saved_closed_caption.txt (Zoom transcript text)
Output:
  - <date>_anonymized.txt
  - <date>_summary.md
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import httpx

EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
PHONE_RE = re.compile(r"\b(?:\+?\d[\d\s().-]{7,}\d)\b")
URL_RE = re.compile(r"\bhttps?://[^\s]+")
TIMESTAMP_RE = re.compile(r"^\s*(?:\d{1,2}:){1,2}\d{2}(?:\.\d+)?\s*$")
SPEAKER_PREFIX_RE = re.compile(
    r"^\s*(?:(?:\d{1,2}:){1,2}\d{2}(?:\.\d+)?\s+)?([A-Za-z][A-Za-z .'\-]{1,60}):\s*(.+)\s*$"
)
WHITESPACE_RE = re.compile(r"\s+")


@dataclass
class PlaceholderMap:
    people: Dict[str, str]
    orgs: Dict[str, str]
    misc: Dict[str, str]


def _normalize_space(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text).strip()


def clean_caption_lines(raw_text: str) -> List[str]:
    """Keep meaningful transcript content and drop obvious timestamp-only lines."""
    out: List[str] = []
    for line in raw_text.splitlines():
        stripped = _normalize_space(line)
        if not stripped:
            continue
        if TIMESTAMP_RE.match(stripped):
            continue
        out.append(stripped)
    return out


def parse_speaker_utterances(lines: Sequence[str]) -> List[Tuple[str | None, str]]:
    """
    Parse Zoom-style lines into (speaker, text).
    If no speaker prefix exists, speaker is None.
    """
    utterances: List[Tuple[str | None, str]] = []
    for line in lines:
        match = SPEAKER_PREFIX_RE.match(line)
        if match:
            speaker = _normalize_space(match.group(1))
            text = _normalize_space(match.group(2))
            if text:
                utterances.append((speaker, text))
            continue
        utterances.append((None, line))
    return utterances


def _build_entity_maps(utterances: Sequence[Tuple[str | None, str]]) -> PlaceholderMap:
    people: Dict[str, str] = {}
    orgs: Dict[str, str] = {}
    misc: Dict[str, str] = {}

    for speaker, _ in utterances:
        if speaker and speaker not in people:
            people[speaker] = f"PERSON_{len(people) + 1:02d}"

    return PlaceholderMap(people=people, orgs=orgs, misc=misc)


def _replace_pattern(text: str, pattern: re.Pattern[str], label: str) -> str:
    index = 0

    def _repl(_: re.Match[str]) -> str:
        nonlocal index
        index += 1
        return f"{label}_{index:02d}"

    return pattern.sub(_repl, text)


def anonymize_utterances(utterances: Sequence[Tuple[str | None, str]]) -> Tuple[str, PlaceholderMap]:
    mapping = _build_entity_maps(utterances)
    lines: List[str] = []

    # Replace longer names first to avoid partial replacement.
    sorted_people = sorted(mapping.people.keys(), key=len, reverse=True)
    people_patterns = [
        (name, re.compile(rf"\b{re.escape(name)}\b", flags=re.IGNORECASE))
        for name in sorted_people
    ]

    for speaker, text in utterances:
        safe = text
        safe = _replace_pattern(safe, EMAIL_RE, "EMAIL")
        safe = _replace_pattern(safe, PHONE_RE, "PHONE")
        safe = _replace_pattern(safe, URL_RE, "URL")

        for name, pattern in people_patterns:
            safe = pattern.sub(mapping.people[name], safe)

        if speaker:
            line = f"{mapping.people[speaker]}: {safe}"
        else:
            line = safe
        lines.append(_normalize_space(line))

    return "\n".join(lines), mapping


def _chunk_text(text: str, max_chars: int = 7000) -> List[str]:
    """Chunk by paragraphs with a character budget."""
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: List[str] = []
    current: List[str] = []
    current_len = 0
    for p in paragraphs:
        p_len = len(p) + 1
        if current and current_len + p_len > max_chars:
            chunks.append("\n".join(current))
            current = [p]
            current_len = p_len
        else:
            current.append(p)
            current_len += p_len
    if current:
        chunks.append("\n".join(current))
    return chunks


def _ollama_generate(prompt: str, model: str, ollama_url: str, timeout_s: int) -> str:
    payload = {"model": model, "prompt": prompt, "stream": False}
    endpoint = f"{ollama_url.rstrip('/')}/api/generate"
    with httpx.Client(timeout=timeout_s) as client:
        response = client.post(endpoint, json=payload)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            body = response.text.strip()
            if response.status_code == 404 and "model" in body.lower():
                raise RuntimeError(
                    f"Ollama model '{model}' is not available locally. "
                    f"Run: ollama pull {model}"
                ) from error
            if response.status_code == 404:
                raise RuntimeError(
                    "Received 404 from the Ollama endpoint. "
                    f"Check that '{ollama_url}' is an Ollama server and that '/api/generate' is available. "
                    f"Response body: {body}"
                ) from error
            raise RuntimeError(
                f"Ollama request failed with status {response.status_code}. Response body: {body}"
            ) from error
        data = response.json()
    text = data.get("response", "").strip()
    if not text:
        raise ValueError("Ollama returned an empty response")
    return text


def summarize_anonymized_text(anonymized_text: str, model: str, ollama_url: str, timeout_s: int) -> str:
    chunks = _chunk_text(anonymized_text, max_chars=7000)
    partial_summaries: List[str] = []

    for i, chunk in enumerate(chunks, start=1):
        prompt = (
            "You summarize anonymized Zoom meeting transcripts.\n"
            "The transcript uses placeholders (PERSON_01, EMAIL_01, etc.).\n"
            "Never infer or invent real identities.\n"
            "Return concise bullet points under:\n"
            "- Key Updates\n- Decisions\n- Risks/Blockers\n- Action Items\n\n"
            f"Transcript chunk {i}/{len(chunks)}:\n{chunk}\n"
        )
        partial_summaries.append(
            _ollama_generate(prompt=prompt, model=model, ollama_url=ollama_url, timeout_s=timeout_s)
        )

    final_prompt = (
        "You are producing the final daily summary from chunk summaries.\n"
        "Keep all placeholders anonymized exactly as provided.\n"
        "Output strict markdown with these sections only:\n"
        "## Daily Summary\n"
        "## Key Updates\n"
        "## Decisions\n"
        "## Risks and Blockers\n"
        "## Action Items\n"
        "## Open Questions\n\n"
        "Chunk summaries:\n"
        + "\n\n---\n\n".join(partial_summaries)
    )
    return _ollama_generate(
        prompt=final_prompt, model=model, ollama_url=ollama_url, timeout_s=timeout_s
    )


def _today_date_string() -> str:
    return datetime.now().strftime("%Y_%m_%d")


def _default_output_dir() -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    return Path(repo_root, "temp", "zoom_summaries")


def verify_ollama_server(ollama_url: str, timeout_s: int) -> None:
    tags_endpoint = f"{ollama_url.rstrip('/')}/api/tags"
    try:
        with httpx.Client(timeout=timeout_s) as client:
            response = client.get(tags_endpoint)
    except httpx.HTTPError as error:
        raise RuntimeError(
            f"Could not connect to Ollama at '{ollama_url}'. "
            "Start Ollama and retry (for example: `ollama serve`)."
        ) from error

    if response.status_code == 404:
        raise RuntimeError(
            f"'{ollama_url}' responded but does not expose Ollama '/api/tags'. "
            "Check --ollama_url and ensure this is an Ollama server."
        )

    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        raise RuntimeError(
            f"Ollama health check failed with status {response.status_code}: {response.text.strip()}"
        ) from error


def run_pipeline(
    input_path: Path,
    output_dir: Path,
    run_date: str,
    model: str,
    ollama_url: str,
    timeout_s: int,
) -> Tuple[Path, Path]:
    raw_text = input_path.read_text(encoding="utf-8", errors="replace")
    lines = clean_caption_lines(raw_text)
    utterances = parse_speaker_utterances(lines)
    anonymized_text, mapping = anonymize_utterances(utterances)
    summary_md = summarize_anonymized_text(
        anonymized_text=anonymized_text, model=model, ollama_url=ollama_url, timeout_s=timeout_s
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    anonymized_path = Path(output_dir, f"{run_date}_anonymized.txt")
    summary_path = Path(output_dir, f"{run_date}_summary.md")
    mapping_path = Path(output_dir, f"{run_date}_anonymization_map.json")

    anonymized_path.write_text(anonymized_text + "\n", encoding="utf-8")
    summary_path.write_text(summary_md.strip() + "\n", encoding="utf-8")
    mapping_path.write_text(
        json.dumps({"people": mapping.people, "orgs": mapping.orgs, "misc": mapping.misc}, indent=2),
        encoding="utf-8",
    )
    return anonymized_path, summary_path


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Daily local Zoom transcript summarizer (anonymized first)")
    parser.add_argument("--input", required=True, help="Path to meeting_saved_closed_caption.txt")
    parser.add_argument("--output_dir", default=str(_default_output_dir()), help="Directory for outputs")
    parser.add_argument("--date", default=_today_date_string(), help="Date stamp for output filenames (YYYY_MM_DD)")
    parser.add_argument("--model", default="qwen2.5:7b-instruct", help="Local Ollama model name")
    parser.add_argument("--ollama_url", default="http://localhost:11434", help="Base URL for local Ollama")
    parser.add_argument("--timeout_s", type=int, default=120, help="HTTP timeout for each model call")
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.is_file():
        raise FileNotFoundError(f"Transcript file not found: {input_path}")

    verify_ollama_server(args.ollama_url, args.timeout_s)

    output_dir = Path(args.output_dir)
    anonymized_path, summary_path = run_pipeline(
        input_path=input_path,
        output_dir=output_dir,
        run_date=args.date,
        model=args.model,
        ollama_url=args.ollama_url,
        timeout_s=args.timeout_s,
    )
    print(f"Anonymized transcript: {anonymized_path}")
    print(f"Daily summary: {summary_path}")


if __name__ == "__main__":
    main()

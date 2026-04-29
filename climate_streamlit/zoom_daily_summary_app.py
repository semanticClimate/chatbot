"""
Simple Streamlit UI for local Zoom transcript summarization.

Features:
- Directory picker for Zoom session folders.
- Raw transcript cleaning (no anonymization stage).
- Editable markdown summary text area.
- Safe output filenames with no spaces and timestamp suffix.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List

import streamlit as st

from zoom_daily_summary import (
    SUMMARY_WARNING,
    apply_name_aliases_to_text,
    apply_regex_name_corrections_to_text,
    attendees_markdown_table,
    clean_caption_lines,
    collect_session_attendees,
    parse_speaker_utterances,
    prepend_warning_and_attendees,
    summarize_transcript_text,
    verify_ollama_server,
)

TRANSCRIPT_FILENAME = "meeting_saved_closed_caption.txt"


def _timestamp_now() -> str:
    """Timestamp used in output filenames: YYYY_MM_DD_HH_MM."""
    return datetime.now().strftime("%Y_%m_%d_%H_%M")


def _list_session_dirs(base_dir: Path) -> List[Path]:
    """List direct subdirectories in most-recent-first order."""
    if not base_dir.is_dir():
        return []
    dirs = [p for p in base_dir.iterdir() if p.is_dir()]
    return sorted(dirs, key=lambda p: p.stat().st_mtime, reverse=True)


def _default_output_dir() -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    return Path(repo_root, "temp", "zoom_summaries")


def _default_config_dir() -> Path:
    """Persistent config directory for name-correction settings."""
    repo_root = Path(__file__).resolve().parents[1]
    return Path(repo_root, "config", "zoom_daily_summary")


def _default_alias_map_path() -> Path:
    """Permanent JSON file for ongoing speaker-name corrections."""
    return Path(_default_config_dir(), "speaker_aliases.json")


def _default_regex_corrections_path() -> Path:
    """Permanent JSON file for regex-based name corrections."""
    return Path(_default_config_dir(), "speaker_name_regex_corrections.json")


def _parse_alias_map(value: str) -> dict[str, str]:
    """
    Parse alias mapping JSON for speaker normalization.

    Expected format:
    {"Alina": "Aleena", "Alyna": "Aleena"}
    """
    if not value.strip():
        return {}
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError("Alias mapping must be a JSON object.")
    return {str(k): str(v) for k, v in parsed.items() if str(k).strip() and str(v).strip()}


def _load_alias_map_from_file(path: Path) -> dict[str, str]:
    """Load alias map from disk; return empty map if missing/invalid."""
    if not path.is_file():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {str(k): str(v) for k, v in parsed.items() if str(k).strip() and str(v).strip()}


def _save_alias_map_to_file(path: Path, alias_map: dict[str, str]) -> None:
    """Persist alias corrections for later sessions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(alias_map, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _parse_regex_corrections(value: str) -> list[tuple[str, str]]:
    """
    Parse regex replacement rows from JSON.

    Expected format:
    [
      {"pattern": "\\bA[l1]ina\\b", "replacement": "Aleena"}
    ]
    """
    if not value.strip():
        return []
    parsed = json.loads(value)
    if not isinstance(parsed, list):
        raise ValueError("Regex corrections must be a JSON array.")
    rows: list[tuple[str, str]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        pattern = str(item.get("pattern", "")).strip()
        replacement = str(item.get("replacement", "")).strip()
        if pattern and replacement:
            rows.append((pattern, replacement))
    return rows


def _load_regex_corrections_from_file(path: Path) -> list[dict[str, str]]:
    """Load regex corrections from disk; return empty list if missing/invalid."""
    if not path.is_file():
        return []
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []
    cleaned: list[dict[str, str]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        pattern = str(item.get("pattern", "")).strip()
        replacement = str(item.get("replacement", "")).strip()
        if pattern and replacement:
            cleaned.append({"pattern": pattern, "replacement": replacement})
    return cleaned


def _save_regex_corrections_to_file(path: Path, rows: list[dict[str, str]]) -> None:
    """Persist regex corrections for later sessions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    st.set_page_config(page_title="Zoom Daily Summary Editor", page_icon="📝", layout="wide")
    st.title("📝 Zoom Daily Summary Editor")
    st.caption("Pick a Zoom session folder, generate summary.md, edit it, then save.")

    if "transcript_text" not in st.session_state:
        st.session_state.transcript_text = ""
    if "summary_md" not in st.session_state:
        st.session_state.summary_md = ""
    if "utterances" not in st.session_state:
        st.session_state.utterances = []
    if "attendees_md" not in st.session_state:
        st.session_state.attendees_md = ""
    if "selected_transcript" not in st.session_state:
        st.session_state.selected_transcript = ""
    if "alias_map_json" not in st.session_state:
        persisted = _load_alias_map_from_file(_default_alias_map_path())
        if "Alina" not in persisted:
            persisted["Alina"] = "Aleena"
        st.session_state.alias_map_json = json.dumps(persisted, indent=2, sort_keys=True)
    if "regex_corrections_json" not in st.session_state:
        persisted_regex = _load_regex_corrections_from_file(_default_regex_corrections_path())
        if not persisted_regex:
            persisted_regex = [{"pattern": r"\bA[l1]ina\b", "replacement": "Aleena"}]
        st.session_state.regex_corrections_json = json.dumps(persisted_regex, indent=2)

    with st.sidebar:
        st.subheader("Settings")
        model = st.text_input("Ollama model", value="qwen2.5:7b-instruct")
        ollama_url = st.text_input("Ollama URL", value="http://localhost:11434")
        timeout_s = st.number_input("Timeout (seconds)", min_value=10, max_value=600, value=120, step=10)
        output_dir_input = st.text_input("Output directory", value=str(_default_output_dir()))
        alias_map_json = st.text_area(
            "Speaker name corrections (JSON)",
            value=st.session_state.alias_map_json,
            height=120,
            help=(
                "Permanent corrections saved to speaker_aliases.json. "
                "Used for attendee extraction and transcript text normalization before summarization."
            ),
        )
        regex_corrections_json = st.text_area(
            "Speaker name regex corrections (JSON)",
            value=st.session_state.regex_corrections_json,
            height=120,
            help="Regex rows are applied in order using case-insensitive matching.",
        )
        st.caption(f"Alias file: `{_default_alias_map_path()}`")
        st.caption(f"Regex file: `{_default_regex_corrections_path()}`")
    st.subheader("1) Select Zoom Session Directory")
    base_default = str(Path.home() / "Documents" / "Zoom")
    transcript_source = st.radio(
        "Transcript source",
        options=["Zoom session directory", "Local transcript file path"],
        index=0,
    )
    if transcript_source == "Zoom session directory":
        base_dir_input = st.text_input("Base Zoom directory", value=base_default)
        base_dir = Path(base_dir_input).expanduser()
        session_dirs = _list_session_dirs(base_dir)
        if not session_dirs:
            st.warning(f"No session folders found in: {base_dir}")
            return
        selected_dir = st.selectbox(
            "Session folder",
            options=session_dirs,
            format_func=lambda p: p.name,
        )
        transcript_path = Path(selected_dir, TRANSCRIPT_FILENAME)
    else:
        local_path_input = st.text_input("Transcript file path", value=st.session_state.selected_transcript)
        transcript_path = Path(local_path_input).expanduser()
    st.session_state.selected_transcript = str(transcript_path)
    st.code(str(transcript_path))

    if not transcript_path.is_file():
        st.error(f"Transcript file not found: {transcript_path}")
        return

    if st.button("Load transcript", type="primary"):
        raw_text = transcript_path.read_text(encoding="utf-8", errors="replace")
        lines = clean_caption_lines(raw_text)
        st.session_state.transcript_text = "\n".join(lines)
        st.session_state.utterances = parse_speaker_utterances(lines)
        st.success(f"Loaded {len(lines)} cleaned transcript lines.")

    st.subheader("2) Generate Summary")
    if not st.session_state.transcript_text:
        st.info("Load a transcript first.")
        return

    if st.button("Generate summary.md", type="primary"):
        try:
            alias_map = _parse_alias_map(alias_map_json)
            regex_rows = _parse_regex_corrections(regex_corrections_json)
        except ValueError as error:
            st.error(str(error))
            return
        _save_alias_map_to_file(_default_alias_map_path(), alias_map)
        st.session_state.alias_map_json = json.dumps(alias_map, indent=2, sort_keys=True)
        regex_rows_for_storage = [{"pattern": pattern, "replacement": replacement} for pattern, replacement in regex_rows]
        _save_regex_corrections_to_file(_default_regex_corrections_path(), regex_rows_for_storage)
        st.session_state.regex_corrections_json = json.dumps(regex_rows_for_storage, indent=2)

        attendees = collect_session_attendees(
            st.session_state.utterances, alias_map=alias_map, regex_corrections=regex_rows
        )
        st.session_state.attendees_md = attendees_markdown_table(attendees).strip()
        normalized_transcript = apply_name_aliases_to_text(st.session_state.transcript_text, alias_map)
        normalized_transcript = apply_regex_name_corrections_to_text(normalized_transcript, regex_rows)

        with st.spinner("Checking Ollama and generating summary..."):
            verify_ollama_server(ollama_url=ollama_url, timeout_s=int(timeout_s))
            summary_md = summarize_transcript_text(
                transcript_text=normalized_transcript,
                model=model,
                ollama_url=ollama_url,
                timeout_s=int(timeout_s),
            )
        st.session_state.summary_md = summary_md.strip()
        st.success("Generated summary.md from normalized transcript, with attendees extracted.")

    if st.session_state.attendees_md:
        st.subheader("Attendees (per session)")
        st.markdown(st.session_state.attendees_md)

    st.subheader("3) Edit summary.md")
    if not st.session_state.summary_md:
        st.info("Generate summary first.")
        return

    st.warning(SUMMARY_WARNING)

    edited_summary = st.text_area(
        "Summary markdown",
        value=st.session_state.summary_md,
        height=420,
    )

    st.subheader("4) Save summary.md")
    if st.button("Save edited summary.md", type="primary"):
        if not edited_summary.strip():
            st.error("Summary is empty.")
            return

        output_dir = Path(output_dir_input).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        stamp = _timestamp_now()
        summary_path = Path(output_dir, f"{stamp}_summary.md")
        full_summary = prepend_warning_and_attendees(
            summary_md=edited_summary,
            attendees_md=st.session_state.attendees_md,
        )
        summary_path.write_text(full_summary + "\n", encoding="utf-8")
        st.session_state.summary_md = edited_summary

        st.success("Saved summary.")
        st.write(f"- Summary: `{summary_path}`")


if __name__ == "__main__":
    main()

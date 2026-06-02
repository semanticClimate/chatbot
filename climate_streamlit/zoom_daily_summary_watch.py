"""
Watch a Zoom recordings directory and summarize new transcripts.

Designed for cron on macOS: scans session folders for
meeting_saved_closed_caption.txt, skips already-processed files (by path + mtime),
waits until a file is stable, then runs the same summarization path as the
Streamlit editor (aliases/regex, no anonymization).
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zoom_daily_summary import (
    apply_name_aliases_to_text,
    apply_regex_name_corrections_to_text,
    attendees_markdown_table,
    clean_caption_lines,
    collect_session_attendees,
    extract_zoom_meeting_id,
    parse_speaker_utterances,
    prepend_warning_and_attendees,
    session_date_for_summary,
    summarize_transcript_text,
    summary_path_for_session,
    verify_ollama_server,
)
from zoom_slack import (
    SlackSettings,
    collect_zoom_session_files,
    load_slack_settings,
    upload_zoom_session_files,
)

TRANSCRIPT_FILENAME = "meeting_saved_closed_caption.txt"
STATE_FILENAME = "processed_transcripts.json"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _default_zoom_dir() -> Path:
    return Path.home() / "Documents" / "Zoom"


def _default_config_dir() -> Path:
    return _repo_root() / "config" / "zoom_daily_summary"


def _default_state_path() -> Path:
    return _default_config_dir() / STATE_FILENAME


def _alias_map_path() -> Path:
    return _default_config_dir() / "speaker_aliases.json"


def _regex_corrections_path() -> Path:
    return _default_config_dir() / "speaker_name_regex_corrections.json"


def _slack_config_path() -> Path:
    return _default_config_dir() / "slack.json"


def discover_transcripts(zoom_dir: Path) -> list[Path]:
    """Return transcript paths under zoom_dir, newest session folders first."""
    if not zoom_dir.is_dir():
        return []
    found: list[Path] = []
    for session_dir in zoom_dir.iterdir():
        if not session_dir.is_dir():
            continue
        transcript = session_dir / TRANSCRIPT_FILENAME
        if transcript.is_file():
            found.append(transcript)
    return sorted(found, key=lambda p: p.stat().st_mtime, reverse=True)


def is_transcript_stable(transcript: Path, min_age_seconds: float, now: float | None = None) -> bool:
    """True when the transcript has not been modified for min_age_seconds."""
    clock = time.time() if now is None else now
    age_s = clock - transcript.stat().st_mtime
    return age_s >= min_age_seconds


def load_state(state_path: Path) -> dict[str, Any]:
    if not state_path.is_file():
        return {}
    try:
        parsed = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def save_state(state_path: Path, state: dict[str, Any]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_alias_map(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(parsed, dict):
        return {}
    return {str(k): str(v) for k, v in parsed.items() if str(k).strip() and str(v).strip()}


def _load_regex_corrections(path: Path) -> list[tuple[str, str]]:
    if not path.is_file():
        return []
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []
    rows: list[tuple[str, str]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        pattern = str(item.get("pattern", "")).strip()
        replacement = str(item.get("replacement", "")).strip()
        if pattern and replacement:
            rows.append((pattern, replacement))
    return rows


def should_process(
    transcript: Path,
    state: dict[str, Any],
    min_age_seconds: float,
    *,
    now: float | None = None,
    force: bool = False,
    slack_enabled: bool = False,
) -> bool:
    """Whether this transcript should be summarized on this run."""
    if force:
        return is_transcript_stable(transcript, min_age_seconds, now=now)
    key = str(transcript.resolve())
    mtime = transcript.stat().st_mtime
    entry = state.get(key)
    if isinstance(entry, dict) and entry.get("mtime") == mtime:
        if slack_enabled and not entry.get("slack_uploaded"):
            summary_path = Path(str(entry.get("summary_path", "")))
            return summary_path.is_file()
        return False
    return is_transcript_stable(transcript, min_age_seconds, now=now)


def _needs_slack_retry(entry: dict[str, Any], slack_enabled: bool) -> bool:
    if not slack_enabled:
        return False
    if entry.get("slack_uploaded"):
        return False
    summary_path = Path(str(entry.get("summary_path", "")))
    return summary_path.is_file()


def process_transcript(
    transcript: Path,
    *,
    model: str,
    ollama_url: str,
    timeout_s: int,
    alias_map: dict[str, str],
    regex_corrections: list[tuple[str, str]],
) -> Path:
    session_dir = transcript.parent
    meeting_id = extract_zoom_meeting_id(session_dir)
    session_date = session_date_for_summary(session_dir, transcript)
    raw_text = transcript.read_text(encoding="utf-8", errors="replace")
    lines = clean_caption_lines(raw_text)
    utterances = parse_speaker_utterances(lines)
    attendees = collect_session_attendees(
        utterances, alias_map=alias_map, regex_corrections=regex_corrections
    )
    attendees_md = attendees_markdown_table(attendees).strip()
    normalized = apply_name_aliases_to_text("\n".join(lines), alias_map)
    normalized = apply_regex_name_corrections_to_text(normalized, regex_corrections)
    summary_md = summarize_transcript_text(
        transcript_text=normalized,
        model=model,
        ollama_url=ollama_url,
        timeout_s=timeout_s,
    )
    full_summary = prepend_warning_and_attendees(
        summary_md=summary_md.strip(),
        attendees_md=attendees_md,
        session_date=session_date,
        meeting_id=meeting_id,
    )

    summary_path = summary_path_for_session(session_dir, meeting_id)
    summary_path.write_text(full_summary.strip() + "\n", encoding="utf-8")
    return summary_path


def _describe_slack_upload(
    settings: SlackSettings,
    *,
    summary_path: Path,
    transcript: Path,
) -> str:
    if settings.upload_all_session_files:
        plan = collect_zoom_session_files(
            transcript.parent,
            summary_path=summary_path,
            exclude_names=settings.exclude_names,
            max_file_bytes=settings.max_file_bytes,
            include_session_dir=True,
        )
        names = ", ".join(p.name for p in plan.upload_paths)
        skipped = len(plan.skipped)
        extra = f"; {skipped} skipped" if skipped else ""
        return f"upload {len(plan.upload_paths)} file(s) to {settings.channel_id}: {names}{extra}"
    parts = [summary_path.name]
    if settings.upload_transcript:
        parts.append(transcript.name)
    return f"upload to {settings.channel_id}: {', '.join(parts)}"


def _upload_to_slack(
    settings: SlackSettings,
    *,
    summary_path: Path,
    transcript: Path,
    slack_timeout_s: float,
) -> None:
    upload_zoom_session_files(
        settings,
        summary_path=summary_path,
        transcript_path=transcript,
        session_name=transcript.parent.name,
        timeout_s=slack_timeout_s,
    )
    print(f"Slack: uploaded to channel {settings.channel_id}")


def run_watch(
    *,
    zoom_dir: Path,
    state_path: Path,
    model: str,
    ollama_url: str,
    timeout_s: int,
    min_age_minutes: float,
    dry_run: bool,
    force_paths: list[Path],
    slack_settings: SlackSettings | None,
    slack_timeout_s: float,
    require_slack: bool,
) -> list[Path]:
    min_age_seconds = min_age_minutes * 60.0
    state = load_state(state_path)
    alias_map = _load_alias_map(_alias_map_path())
    regex_corrections = _load_regex_corrections(_regex_corrections_path())
    slack_enabled = slack_settings is not None

    if require_slack and not slack_enabled:
        raise RuntimeError(
            "Slack upload required but SLACK_BOT_TOKEN / SLACK_CHANNEL_ID are not set. "
            "Copy config/zoom_daily_summary/slack.env.example to slack.env."
        )

    if force_paths:
        candidates = [p.resolve() for p in force_paths]
    else:
        candidates = discover_transcripts(zoom_dir)

    written: list[Path] = []
    for transcript in candidates:
        if not transcript.is_file():
            continue
        key = str(transcript.resolve())
        entry = state.get(key)
        entry_dict = entry if isinstance(entry, dict) else {}

        if not should_process(
            transcript,
            state,
            min_age_seconds,
            force=bool(force_paths),
            slack_enabled=slack_enabled,
        ):
            continue

        if _needs_slack_retry(entry_dict, slack_enabled):
            summary_path = Path(str(entry_dict["summary_path"]))
            if dry_run:
                if slack_settings is not None:
                    print(
                        f"[dry-run] would {_describe_slack_upload(slack_settings, summary_path=summary_path, transcript=transcript)}"
                    )
                continue
            if slack_settings is None:
                continue
            _upload_to_slack(
                slack_settings,
                summary_path=summary_path,
                transcript=transcript,
                slack_timeout_s=slack_timeout_s,
            )
            entry_dict["slack_uploaded"] = True
            entry_dict["slack_uploaded_at"] = datetime.now(timezone.utc).isoformat()
            state[key] = entry_dict
            save_state(state_path, state)
            written.append(summary_path)
            continue

        if dry_run:
            msg = f"[dry-run] would summarize: {transcript}"
            if slack_settings is not None:
                pending_summary = summary_path_for_session(transcript.parent)
                msg += f" (then {_describe_slack_upload(slack_settings, summary_path=pending_summary, transcript=transcript)})"
            print(msg)
            continue

        verify_ollama_server(ollama_url=ollama_url, timeout_s=timeout_s)
        summary_path = process_transcript(
            transcript,
            model=model,
            ollama_url=ollama_url,
            timeout_s=timeout_s,
            alias_map=alias_map,
            regex_corrections=regex_corrections,
        )
        slack_uploaded = False
        if slack_settings is not None:
            _upload_to_slack(
                slack_settings,
                summary_path=summary_path,
                transcript=transcript,
                slack_timeout_s=slack_timeout_s,
            )
            slack_uploaded = True

        state[key] = {
            "mtime": transcript.stat().st_mtime,
            "summary_path": str(summary_path),
            "meeting_id": extract_zoom_meeting_id(transcript.parent),
            "session_date": session_date_for_summary(transcript.parent, transcript),
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "session_dir": str(transcript.parent),
            "slack_uploaded": slack_uploaded,
        }
        if slack_uploaded:
            state[key]["slack_uploaded_at"] = datetime.now(timezone.utc).isoformat()
        save_state(state_path, state)
        written.append(summary_path)
        print(f"Summary: {summary_path}")

    return written


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Discover new Zoom transcripts and write summary markdown files."
    )
    parser.add_argument(
        "--zoom-dir",
        default=str(_default_zoom_dir()),
        help="Zoom base directory (session folders are direct children)",
    )
    parser.add_argument(
        "--state-file",
        default=str(_default_state_path()),
        help="JSON file tracking processed transcript path + mtime",
    )
    parser.add_argument(
        "--min-age-minutes",
        type=float,
        default=10.0,
        help="Skip transcripts modified within this many minutes (Zoom may still be writing)",
    )
    parser.add_argument("--model", default="qwen2.5:7b-instruct", help="Ollama model name")
    parser.add_argument("--ollama-url", default="http://localhost:11434", help="Ollama base URL")
    parser.add_argument("--timeout-s", type=int, default=120, help="HTTP timeout per model call")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List transcripts that would be processed without calling Ollama",
    )
    parser.add_argument(
        "--force",
        action="append",
        default=[],
        metavar="TRANSCRIPT",
        help="Re-summarize a specific meeting_saved_closed_caption.txt (repeatable)",
    )
    parser.add_argument(
        "--slack-channel",
        default="",
        help="Slack channel ID (overrides SLACK_CHANNEL_ID / slack.json)",
    )
    parser.add_argument(
        "--skip-slack",
        action="store_true",
        help="Do not upload files to Slack even if credentials are configured",
    )
    parser.add_argument(
        "--require-slack",
        action="store_true",
        help="Fail if Slack credentials are missing (useful for cron)",
    )
    parser.add_argument(
        "--slack-timeout-s",
        type=float,
        default=120.0,
        help="HTTP timeout for Slack file uploads",
    )
    parser.add_argument(
        "--slack-upload-all-session-files",
        action="store_true",
        default=None,
        help="Upload every file in the Zoom session folder (not only summary + transcript)",
    )
    parser.add_argument(
        "--no-slack-upload-all-session-files",
        action="store_true",
        help="Upload only summary.md and transcript (overrides env/slack.json)",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    force_paths = [Path(p).expanduser() for p in args.force]
    upload_all: bool | None = None
    if args.no_slack_upload_all_session_files:
        upload_all = False
    elif args.slack_upload_all_session_files:
        upload_all = True

    slack_settings = load_slack_settings(
        config_path=_slack_config_path(),
        channel_id_override=args.slack_channel or None,
        skip_slack=args.skip_slack,
        upload_all_session_files=upload_all,
    )
    written = run_watch(
        zoom_dir=Path(args.zoom_dir).expanduser(),
        state_path=Path(args.state_file).expanduser(),
        model=args.model,
        ollama_url=args.ollama_url,
        timeout_s=args.timeout_s,
        min_age_minutes=args.min_age_minutes,
        dry_run=args.dry_run,
        force_paths=force_paths,
        slack_settings=slack_settings,
        slack_timeout_s=args.slack_timeout_s,
        require_slack=args.require_slack,
    )
    if not written and not args.dry_run:
        print("No new transcripts to summarize.")


if __name__ == "__main__":
    main()

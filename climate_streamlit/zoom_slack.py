"""
Post Zoom summary and session files to a Slack channel (Slack Web API).

Requires a bot token with scopes: files:write, chat:write (invite the bot to the channel).
"""

from __future__ import annotations

import fnmatch
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

SLACK_API_BASE = "https://slack.com/api"
# Slack may error above ~14 files per files.completeUploadExternal; batch conservatively.
SLACK_UPLOAD_BATCH_SIZE = 10
DEFAULT_MAX_FILE_MB = 1024
DEFAULT_EXCLUDE_NAMES = [".DS_Store", "Thumbs.db", "desktop.ini"]


@dataclass(frozen=True)
class SlackSettings:
    token: str
    channel_id: str
    upload_transcript: bool = True
    upload_all_session_files: bool = False
    max_file_bytes: int = DEFAULT_MAX_FILE_MB * 1024 * 1024
    exclude_names: tuple[str, ...] = tuple(DEFAULT_EXCLUDE_NAMES)
    initial_comment: str | None = None


@dataclass
class SessionUploadPlan:
    """Files to upload and any skipped paths with reasons."""

    upload_paths: list[Path] = field(default_factory=list)
    skipped: list[tuple[Path, str]] = field(default_factory=list)


def _env_flag(name: str) -> bool | None:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return None
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return None


def _load_slack_json(config_path: Path) -> dict[str, Any]:
    if not config_path.is_file():
        return {}
    try:
        parsed = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _parse_exclude_names(file_cfg: dict[str, Any]) -> tuple[str, ...]:
    raw = file_cfg.get("exclude_names", DEFAULT_EXCLUDE_NAMES)
    if not isinstance(raw, list):
        return tuple(DEFAULT_EXCLUDE_NAMES)
    names = [str(item).strip() for item in raw if str(item).strip()]
    return tuple(names) if names else tuple(DEFAULT_EXCLUDE_NAMES)


def load_slack_settings(
    *,
    config_path: Path,
    channel_id_override: str | None = None,
    skip_slack: bool = False,
    upload_all_session_files: bool | None = None,
) -> SlackSettings | None:
    """Return Slack settings when token and channel are configured; else None."""
    if skip_slack:
        return None

    file_cfg = _load_slack_json(config_path)
    token = os.environ.get("SLACK_BOT_TOKEN", "").strip() or str(file_cfg.get("bot_token", "")).strip()
    channel_id = (
        (channel_id_override or "").strip()
        or os.environ.get("SLACK_CHANNEL_ID", "").strip()
        or str(file_cfg.get("channel_id", "")).strip()
    )
    if not token or not channel_id:
        return None

    upload_transcript = file_cfg.get("upload_transcript", True)
    if not isinstance(upload_transcript, bool):
        upload_transcript = True

    upload_all = file_cfg.get("upload_all_session_files", False)
    if not isinstance(upload_all, bool):
        upload_all = False
    env_upload_all = _env_flag("ZOOM_SLACK_UPLOAD_ALL_SESSION_FILES")
    if upload_all_session_files is not None:
        upload_all = upload_all_session_files
    elif env_upload_all is not None:
        upload_all = env_upload_all

    max_file_mb = file_cfg.get("max_file_mb", DEFAULT_MAX_FILE_MB)
    try:
        max_file_bytes = int(float(max_file_mb) * 1024 * 1024)
    except (TypeError, ValueError):
        max_file_bytes = DEFAULT_MAX_FILE_MB * 1024 * 1024

    initial_comment = file_cfg.get("initial_comment")
    if initial_comment is not None:
        initial_comment = str(initial_comment).strip() or None

    return SlackSettings(
        token=token,
        channel_id=channel_id,
        upload_transcript=upload_transcript,
        upload_all_session_files=upload_all,
        max_file_bytes=max_file_bytes,
        exclude_names=_parse_exclude_names(file_cfg),
        initial_comment=initial_comment,
    )


def _matches_exclude(filename: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(filename, pattern) for pattern in patterns)


def _file_upload_status(path: Path, *, exclude_names: tuple[str, ...], max_file_bytes: int) -> str | None:
    """Return a skip reason, or None if the file can be uploaded."""
    if not path.is_file():
        return "not a file"
    if _matches_exclude(path.name, exclude_names):
        return "excluded by name pattern"
    size = path.stat().st_size
    if size > max_file_bytes:
        mb = size / (1024 * 1024)
        limit_mb = max_file_bytes / (1024 * 1024)
        return f"too large ({mb:.1f} MB > {limit_mb:.0f} MB limit)"
    return None


def collect_zoom_session_files(
    session_dir: Path,
    *,
    summary_path: Path | None = None,
    exclude_names: tuple[str, ...],
    max_file_bytes: int,
    include_session_dir: bool,
) -> SessionUploadPlan:
    """
    Build the list of Zoom session files to upload.

    When include_session_dir is True, includes every file in the session folder
    (typical Zoom outputs: transcript, chat, audio, video, etc.).
    summary_path is always listed first when provided.
    """
    plan = SessionUploadPlan()
    seen: set[Path] = set()

    def add(path: Path) -> None:
        resolved = path.resolve()
        if resolved in seen:
            return
        seen.add(resolved)
        reason = _file_upload_status(path, exclude_names=exclude_names, max_file_bytes=max_file_bytes)
        if reason:
            plan.skipped.append((path, reason))
        else:
            plan.upload_paths.append(path)

    if summary_path is not None and summary_path.is_file():
        add(summary_path)

    if include_session_dir and session_dir.is_dir():
        for child in sorted(session_dir.iterdir(), key=lambda p: p.name.lower()):
            if child.is_file():
                add(child)
    elif summary_path is None:
        raise ValueError("No files to collect: session upload disabled and no summary path.")

    return plan


def _slack_error(method: str, payload: dict[str, Any]) -> RuntimeError:
    error = payload.get("error", "unknown_error")
    return RuntimeError(f"Slack API {method} failed: {error}")


def _get_upload_url(client: httpx.Client, token: str, file_path: Path) -> tuple[str, str]:
    length = file_path.stat().st_size
    response = client.post(
        f"{SLACK_API_BASE}/files.getUploadURLExternal",
        headers={"Authorization": f"Bearer {token}"},
        data={"filename": file_path.name, "length": str(length)},
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise _slack_error("files.getUploadURLExternal", payload)
    return str(payload["upload_url"]), str(payload["file_id"])


def _upload_bytes(client: httpx.Client, upload_url: str, file_path: Path) -> None:
    content = file_path.read_bytes()
    response = client.post(
        upload_url,
        content=content,
        headers={"Content-Type": "application/octet-stream"},
    )
    if response.status_code >= 400:
        raise RuntimeError(
            f"Slack file upload to external URL failed with status {response.status_code}"
        )


def _complete_upload(
    client: httpx.Client,
    token: str,
    *,
    channel_id: str,
    file_specs: list[dict[str, str]],
    initial_comment: str | None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "channel_id": channel_id,
        "files": file_specs,
    }
    if initial_comment:
        body["initial_comment"] = initial_comment

    response = client.post(
        f"{SLACK_API_BASE}/files.completeUploadExternal",
        headers={"Authorization": f"Bearer {token}"},
        json=body,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise _slack_error("files.completeUploadExternal", payload)
    return payload


def upload_files_to_channel(
    settings: SlackSettings,
    *,
    file_paths: list[Path],
    initial_comment: str | None = None,
    timeout_s: float = 120.0,
    batch_size: int = SLACK_UPLOAD_BATCH_SIZE,
) -> list[dict[str, Any]]:
    """Upload files into a Slack channel, batching to stay within API limits."""
    paths = [p for p in file_paths if p.is_file()]
    if not paths:
        raise ValueError("No files to upload to Slack.")

    comment = initial_comment if initial_comment is not None else settings.initial_comment
    results: list[dict[str, Any]] = []

    with httpx.Client(timeout=timeout_s) as client:
        for batch_index, start in enumerate(range(0, len(paths), batch_size)):
            batch = paths[start : start + batch_size]
            file_specs: list[dict[str, str]] = []
            for path in batch:
                upload_url, file_id = _get_upload_url(client, settings.token, path)
                _upload_bytes(client, upload_url, path)
                file_specs.append({"id": file_id, "title": path.name})

            batch_comment = comment if batch_index == 0 else None
            results.append(
                _complete_upload(
                    client,
                    settings.token,
                    channel_id=settings.channel_id,
                    file_specs=file_specs,
                    initial_comment=batch_comment,
                )
            )
    return results


def upload_zoom_session_files(
    settings: SlackSettings,
    *,
    summary_path: Path,
    transcript_path: Path,
    session_name: str | None = None,
    timeout_s: float = 120.0,
) -> dict[str, Any]:
    """Upload summary plus Zoom session files (transcript only, or full session folder)."""
    session_dir = transcript_path.parent
    label = session_name or session_dir.name

    if settings.upload_all_session_files:
        plan = collect_zoom_session_files(
            session_dir,
            summary_path=summary_path,
            exclude_names=settings.exclude_names,
            max_file_bytes=settings.max_file_bytes,
            include_session_dir=True,
        )
        for skipped_path, reason in plan.skipped:
            print(f"Slack: skip {skipped_path.name} ({reason})")
        paths = plan.upload_paths
        comment = settings.initial_comment or f"Zoom session files: {label} ({len(paths)} files)"
    else:
        paths = [summary_path]
        if settings.upload_transcript and transcript_path.is_file():
            paths.append(transcript_path)
        comment = settings.initial_comment or f"Zoom session summary: {label}"

    if not paths:
        raise ValueError(f"No uploadable files for session: {session_dir}")

    results = upload_files_to_channel(
        settings,
        file_paths=paths,
        initial_comment=comment,
        timeout_s=timeout_s,
    )
    return results[-1]

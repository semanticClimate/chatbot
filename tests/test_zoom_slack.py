import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from zoom_slack import (
    SlackSettings,
    collect_zoom_session_files,
    load_slack_settings,
    upload_files_to_channel,
)


def test_load_slack_settings_from_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    monkeypatch.setenv("SLACK_CHANNEL_ID", "C123")
    settings = load_slack_settings(config_path=tmp_path / "missing.json", skip_slack=False)
    assert settings is not None
    assert settings.token == "xoxb-test"
    assert settings.channel_id == "C123"


def test_load_slack_settings_upload_all_from_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    monkeypatch.setenv("SLACK_CHANNEL_ID", "C123")
    monkeypatch.setenv("ZOOM_SLACK_UPLOAD_ALL_SESSION_FILES", "1")
    settings = load_slack_settings(config_path=tmp_path / "missing.json", skip_slack=False)
    assert settings is not None
    assert settings.upload_all_session_files is True


def test_load_slack_settings_skip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    settings = load_slack_settings(config_path=tmp_path / "missing.json", skip_slack=True)
    assert settings is None


def test_collect_zoom_session_files_includes_session_folder(tmp_path: Path):
    session = tmp_path / "2026-05-15 meeting"
    session.mkdir()
    (session / "meeting_saved_closed_caption.txt").write_text("caption\n", encoding="utf-8")
    (session / "chat.txt").write_text("chat\n", encoding="utf-8")
    (session / "audio_only.m4a").write_bytes(b"\x00\x01")
    (session / ".DS_Store").write_bytes(b"junk")
    summary = tmp_path / "summary.md"
    summary.write_text("# Summary\n", encoding="utf-8")

    plan = collect_zoom_session_files(
        session,
        summary_path=summary,
        exclude_names=(".DS_Store",),
        max_file_bytes=1024 * 1024,
        include_session_dir=True,
    )
    names = {p.name for p in plan.upload_paths}
    assert names == {"summary.md", "audio_only.m4a", "chat.txt", "meeting_saved_closed_caption.txt"}
    assert any(s[0].name == ".DS_Store" for s in plan.skipped)


def test_collect_zoom_session_files_skips_huge_files(tmp_path: Path):
    session = tmp_path / "session"
    session.mkdir()
    big = session / "video.mp4"
    big.write_bytes(b"x" * 200)
    plan = collect_zoom_session_files(
        session,
        summary_path=None,
        exclude_names=(),
        max_file_bytes=100,
        include_session_dir=True,
    )
    assert plan.upload_paths == []
    assert plan.skipped[0][1].startswith("too large")


def test_upload_files_to_channel_batches(tmp_path: Path):
    files = []
    for i in range(3):
        path = tmp_path / f"file{i}.txt"
        path.write_text(f"content {i}\n", encoding="utf-8")
        files.append(path)
    settings = SlackSettings(token="xoxb-test", channel_id="C123", upload_transcript=False)

    mock_client = MagicMock()

    def make_get_resp(file_id: str):
        resp = MagicMock()
        resp.json.return_value = {
            "ok": True,
            "upload_url": f"https://upload.example/{file_id}",
            "file_id": file_id,
        }
        resp.raise_for_status = MagicMock()
        return resp

    put_resp = MagicMock()
    put_resp.status_code = 200
    complete_resp = MagicMock()
    complete_resp.json.return_value = {"ok": True}
    complete_resp.raise_for_status = MagicMock()

    mock_client.post.side_effect = [
        make_get_resp("F1"),
        put_resp,
        make_get_resp("F2"),
        put_resp,
        make_get_resp("F3"),
        put_resp,
        complete_resp,
    ]
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = False

    with patch("zoom_slack.httpx.Client", return_value=mock_client):
        results = upload_files_to_channel(
            settings, file_paths=files, initial_comment="hi", batch_size=10
        )

    assert len(results) == 1
    assert mock_client.post.call_count == 7

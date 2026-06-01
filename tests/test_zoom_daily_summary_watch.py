import json
import time
from pathlib import Path

from zoom_daily_summary_watch import (
    discover_transcripts,
    is_transcript_stable,
    load_state,
    save_state,
    should_process,
    _needs_slack_retry,
    TRANSCRIPT_FILENAME,
)


def _make_session(zoom_dir: Path, name: str, content: str = "00:01:00 Alice: hello\n") -> Path:
    session = zoom_dir / name
    session.mkdir(parents=True)
    transcript = session / TRANSCRIPT_FILENAME
    transcript.write_text(content, encoding="utf-8")
    return transcript


def test_discover_transcripts_finds_session_files(tmp_path: Path):
    zoom_dir = tmp_path / "Zoom"
    zoom_dir.mkdir()
    t1 = _make_session(zoom_dir, "session_a")
    time.sleep(0.05)
    t2 = _make_session(zoom_dir, "session_b")

    found = discover_transcripts(zoom_dir)
    assert [p.resolve() for p in found] == [t2.resolve(), t1.resolve()], (
        f"Expected newest-first order, got {found}"
    )


def test_is_transcript_stable_respects_min_age(tmp_path: Path):
    transcript = tmp_path / TRANSCRIPT_FILENAME
    transcript.write_text("line\n", encoding="utf-8")
    mtime = transcript.stat().st_mtime
    assert is_transcript_stable(transcript, min_age_seconds=60.0, now=mtime + 30) is False
    assert is_transcript_stable(transcript, min_age_seconds=60.0, now=mtime + 61) is True


def test_should_process_skips_recorded_mtime(tmp_path: Path):
    transcript = tmp_path / TRANSCRIPT_FILENAME
    transcript.write_text("line\n", encoding="utf-8")
    mtime = transcript.stat().st_mtime
    state = {str(transcript.resolve()): {"mtime": mtime}}

    assert should_process(transcript, state, min_age_seconds=0.0, now=mtime + 1) is False


def test_should_process_when_mtime_changes(tmp_path: Path):
    transcript = tmp_path / TRANSCRIPT_FILENAME
    transcript.write_text("line\n", encoding="utf-8")
    old_mtime = transcript.stat().st_mtime
    state = {str(transcript.resolve()): {"mtime": old_mtime}}

    transcript.write_text("line\nmore\n", encoding="utf-8")
    new_mtime = transcript.stat().st_mtime
    assert new_mtime != old_mtime
    assert should_process(transcript, state, min_age_seconds=0.0, now=new_mtime + 1) is True


def test_should_process_retries_slack_when_summary_exists(tmp_path: Path):
    transcript = tmp_path / TRANSCRIPT_FILENAME
    transcript.write_text("line\n", encoding="utf-8")
    summary = tmp_path / "summary.md"
    summary.write_text("# Summary\n", encoding="utf-8")
    mtime = transcript.stat().st_mtime
    state = {
        str(transcript.resolve()): {
            "mtime": mtime,
            "summary_path": str(summary),
            "slack_uploaded": False,
        }
    }
    assert should_process(transcript, state, min_age_seconds=0.0, slack_enabled=True) is True
    assert _needs_slack_retry(state[str(transcript.resolve())], slack_enabled=True) is True


def test_state_round_trip(tmp_path: Path):
    state_path = tmp_path / "processed_transcripts.json"
    payload = {"/tmp/a.txt": {"mtime": 1.0}}
    save_state(state_path, payload)
    loaded = load_state(state_path)
    assert loaded == payload, f"Expected round-trip state, got {loaded}"

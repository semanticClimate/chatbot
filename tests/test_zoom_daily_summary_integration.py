import os
from pathlib import Path

import pytest

from zoom_daily_summary import run_pipeline, verify_ollama_server

DEFAULT_MODEL = "qwen2.5:7b-instruct"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_TIMEOUT_S = 180
CUTDOWN_TRANSCRIPT_PATH = Path("tests", "resources", "zoom_transcript_cutdown.txt")


def test_run_pipeline_with_cutdown_transcript_generates_summary():
    model = os.environ.get("OLLAMA_MODEL", DEFAULT_MODEL)
    ollama_url = os.environ.get("OLLAMA_URL", DEFAULT_OLLAMA_URL)
    timeout_s = int(os.environ.get("OLLAMA_TIMEOUT_S", str(DEFAULT_TIMEOUT_S)))

    try:
        verify_ollama_server(ollama_url=ollama_url, timeout_s=timeout_s)
    except RuntimeError as error:
        pytest.skip(f"Ollama unavailable for integration test: {error}")

    output_dir = Path("temp", "zoom_summaries")
    anonymized_path = Path(output_dir, "integration_2026_04_25_anonymized.txt")
    if anonymized_path.exists():
        anonymized_path.unlink()
    anonymized_path, summary_path = run_pipeline(
        input_path=CUTDOWN_TRANSCRIPT_PATH,
        output_dir=output_dir,
        run_date="integration_2026_04_25",
        model=model,
        ollama_url=ollama_url,
        timeout_s=timeout_s,
    )

    assert not anonymized_path.is_file(), (
        f"Did not expect anonymized output file to be written: {anonymized_path}"
    )
    assert summary_path.is_file(), f"Expected summary output file: {summary_path}"

    summary_text = summary_path.read_text(encoding="utf-8")
    assert summary_text.strip(), f"Expected non-empty summary content in {summary_path}"
    assert "## Attendees" in summary_text, (
        f"Expected attendees section in {summary_path}, got: {summary_text[:300]}"
    )
    assert "## Daily Summary" in summary_text, (
        f"Expected daily summary heading in {summary_path}, got: {summary_text[:300]}"
    )

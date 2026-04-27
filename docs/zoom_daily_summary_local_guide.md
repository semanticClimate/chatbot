# Local Daily Zoom Summary Guide

**Date:** 2026-04-25 (system date of generation)

This project now includes a local script to process Zoom caption transcripts with privacy-first flow:

1. clean transcript lines
2. anonymize people/contact details
3. summarize with local Ollama model

Script: `climate_streamlit/zoom_daily_summary.py`

## Input

- Zoom transcript file: `meeting_saved_closed_caption.txt`
- Ignore `chat.txt` (not used by this script)

## Run

From repository root:

```bash
python climate_streamlit/zoom_daily_summary.py \
  --input "/path/to/meeting_saved_closed_caption.txt"
```

Optional arguments:

- `--output_dir` (default: `temp/zoom_summaries`)
- `--date` (default: current system date, `YYYY_MM_DD`)
- `--model` (default: `qwen2.5:7b-instruct`)
- `--ollama_url` (default: `http://localhost:11434`)
- `--timeout_s` (default: `120`)

## Output files

For date `YYYY_MM_DD`, outputs are:

- `YYYY_MM_DD_anonymized.txt`
- `YYYY_MM_DD_summary.md`
- `YYYY_MM_DD_anonymization_map.json`

These are written under `temp/zoom_summaries` by default.

## Notes

- The script performs anonymization before summarization.
- Placeholder tokens are deterministic within a run (for example: `PERSON_01`).
- Keep the generated anonymization map local/private.

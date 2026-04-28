# Local Daily Zoom Summary Guide

**Date:** 2026-04-25 (system date of generation)

This project now includes tools to process Zoom caption transcripts locally:

1. clean transcript lines
2. summarize with local Ollama model
3. tabulate attendees (speakers) per session
4. optionally edit `summary.md` before final save (Streamlit app)

Script: `climate_streamlit/zoom_daily_summary.py`
UI app: `climate_streamlit/zoom_daily_summary_app.py`

## Input

- Zoom transcript file: `meeting_saved_closed_caption.txt`
- Ignore `chat.txt` (not used by this script)

## Run

From repository root:

```bash
python climate_streamlit/zoom_daily_summary.py \
  --input "/path/to/meeting_saved_closed_caption.txt"
```

Or run the Streamlit UI:

```bash
streamlit run climate_streamlit/zoom_daily_summary_app.py
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

For the Streamlit app, output filename is:

- `YYYY_MM_DD_HH_MM_summary.md`

Default app output directory is `docs/summary`.

## Streamlit editor workflow (no anonymization stage)

1. Choose base Zoom directory (default: `~/Documents/Zoom`)
2. Select a session folder (contains `meeting_saved_closed_caption.txt`)
3. Click **Load transcript**
4. Click **Generate summary.md**
5. Review attendees table (speaker + turn count)
6. Edit summary markdown in the text area
7. Click **Save edited summary.md**

## Notes

- The Streamlit app now skips anonymization and focuses on editable summary output.
- Use **Speaker name corrections (JSON)** in the sidebar to normalize transcription errors (for example `{"Alina":"Aleena"}`).
- The app writes only `summary.md` output (no anonymized transcript or anonymization map files).

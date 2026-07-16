# Epic: Query/response table for CABot evaluation (#8)

Source: [GitHub issue #8](https://github.com/semanticClimate/chatbot/issues/8) — led by @Sai-nikhil2k5 with @Uditaagarwal1.

## Goal

Persist each `query`, model `response`, and optional user comments; export as a table (CSV) for analysis and merge across sessions.

## Existing hooks

- `backend.app/db.py` — interaction logging (`log_interaction`, `get_logs_csv_string`)
- Streamlit admin export paths in legacy `app.py`

## Proposed slices

1. **Export button** in operator UI → download CSV for current session DB
2. **Web client** — optional “save this answer” comment field POSTing to API
3. **Merge tool** — script to combine CSVs from multiple testers

Track sub-tasks as new issues; do not block book-viewer bugs on this epic.

# Local Daily Zoom Summary Guide

**Date:** 2026-04-25 (system date of generation)

This project now includes tools to process Zoom caption transcripts locally:

1. clean transcript lines
2. summarize with local Ollama model
3. tabulate attendees (speakers) per session
4. optionally edit `summary.md` before final save (Streamlit app)

Script: `backend.app/zoom_daily_summary.py`
UI app: `backend.app/zoom_daily_summary_app.py`

## Input

- Zoom transcript file: `meeting_saved_closed_caption.txt`
- Ignore `chat.txt` (not used by this script)

## Run

From repository root:

```bash
python backend.app/zoom_daily_summary.py \
  --input "/path/to/meeting_saved_closed_caption.txt"
```

Or run the Streamlit UI:

```bash
streamlit run backend.app/zoom_daily_summary_app.py
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

For the Streamlit app and watch script, the summary is saved **in the Zoom session folder**:

- `{zoom_meeting_id}_summary.md` (UUID or numeric meeting ID from folder/metadata)

The summary body includes a **Session** section with date and Zoom meeting ID.

## Streamlit editor workflow (no anonymization stage)

1. Choose base Zoom directory (default: `~/Documents/Zoom`)
2. Select a session folder (contains `meeting_saved_closed_caption.txt`)
3. Click **Load transcript**
4. Click **Generate summary.md**
5. Review attendees table (speaker + turn count)
6. Edit summary markdown in the text area
7. Click **Save edited summary.md**

## Automated watch (launchd on your Mac)

If Zoom saves sessions under `~/Documents/Zoom`, you can summarize new transcripts on a schedule without opening Streamlit.

Script: `backend.app/zoom_daily_summary_watch.py`  
Wrapper: `scripts/run_zoom_daily_summary_watch.sh`  
LaunchAgent: `config/launchd/com.chatbot.zoom-daily-summary.plist`

### Schedule (UTC)

The LaunchAgent runs **every day** at:

| UTC  | Local (UK winter, GMT) | Local (UK summer, BST) |
|------|------------------------|-------------------------|
| 09:30 | 09:30 | 10:30 |
| 11:00 | 11:00 | 12:00 |
| 12:00 | 12:00 | 13:00 |
| 18:00 | 18:00 | 19:00 |

Install (writes `~/Library/LaunchAgents/com.chatbot.zoom-daily-summary.plist`):

```bash
chmod +x scripts/install_zoom_daily_summary_launchd.sh
./scripts/install_zoom_daily_summary_launchd.sh
```

Uninstall:

```bash
./scripts/install_zoom_daily_summary_launchd.sh --uninstall
```

Logs: `/tmp/zoom_summary_watch.log`

Check status:

```bash
launchctl print "gui/$(id -u)/com.chatbot.zoom-daily-summary"
```

Dry run (lists new transcripts only):

```bash
./scripts/run_zoom_daily_summary_watch.sh --dry-run
```

Process new stable transcripts (default: skip files modified in the last 10 minutes):

```bash
./scripts/run_zoom_daily_summary_watch.sh
```

Outputs are written beside the transcript: `~/Documents/Zoom/<session>/{meeting_id}_summary.md`.  
Processed transcripts are tracked in `config/zoom_daily_summary/processed_transcripts.json` (by absolute path + file mtime).

Requirements for launchd:

- Ollama running (`ollama serve`) and the model pulled (`ollama pull qwen2.5:7b-instruct`)
- Python venv at `backend.app/venv` (or edit the wrapper to use your interpreter)
- `config/zoom_daily_summary/slack.env` configured (install uses `--require-slack`)
- Mac awake/logged in at scheduled times (launchd does not run while asleep)
- macOS may require **Full Disk Access** for `bash` or Terminal if `~/Documents/Zoom` is not readable

Re-summarize one transcript:

```bash
./scripts/run_zoom_daily_summary_watch.sh --force "/path/to/session/meeting_saved_closed_caption.txt"
```

### Upload to Slack (automatic)

After each new summary, the watch script uploads to Slack. By default (`run_zoom_daily_summary_watch.sh`) it uploads **all files in the Zoom session folder**, for example:

- `meeting_saved_closed_caption.txt` (transcript)
- `chat.txt`
- `audio_only.m4a`, `video*.mp4` (recordings, if present)
- `{zoom_meeting_id}_summary.md` (generated summary, in the same folder)

Files over **1024 MB** are skipped (Slack workspace limit). `.DS_Store` and similar junk names are excluded. Uploads are batched (10 files per Slack message) to stay within API limits.

To upload **only** the summary and transcript, set in `slack.env`:

```bash
ZOOM_SLACK_UPLOAD_ALL_SESSION_FILES=0
```

Or in `slack.json`: `"upload_all_session_files": false`.

**One-time Slack setup**

1. Create an app at [https://api.slack.com/apps](https://api.slack.com/apps).
2. Add bot scopes: `files:write`, `chat:write`.
3. Install the app to your workspace and copy the **Bot User OAuth Token** (`xoxb-...`).
4. Invite the bot to your channel (`/invite @YourBot`).
5. Copy the channel ID (right-click channel → View channel details → copy ID at bottom).

**Configure on your Mac**

```bash
cp config/zoom_daily_summary/slack.env.example config/zoom_daily_summary/slack.env
# edit slack.env — set SLACK_BOT_TOKEN and SLACK_CHANNEL_ID

cp config/zoom_daily_summary/slack.json.example config/zoom_daily_summary/slack.json
# optional: edit upload_transcript / initial_comment
```

Dry run including Slack:

```bash
./scripts/run_zoom_daily_summary_watch.sh --dry-run
```

Skip Slack for one run:

```bash
./scripts/run_zoom_daily_summary_watch.sh --skip-slack
```

If Slack upload fails after the summary was written, the next launchd run retries upload only (no re-summarization).

## Notes

- The Streamlit app now skips anonymization and focuses on editable summary output.
- Use **Speaker name corrections (JSON)** in the sidebar to normalize transcription errors (for example `{"Alina":"Aleena"}`).
- The app writes only `summary.md` output (no anonymized transcript or anonymization map files).
- The watch script uses the same speaker correction JSON files under `config/zoom_daily_summary/`.

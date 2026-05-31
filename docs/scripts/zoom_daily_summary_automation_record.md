# Zoom daily summary automation — discussion record and agreements

**Recorded:** 2026-05-15  
**Participants:** Peter Murray-Rust (Mac host), team (coworker receives outputs in Slack)  
**Related how-to:** [../zoom_daily_summary_local_guide.md](../zoom_daily_summary_local_guide.md)

This document captures what we discussed, what we agreed, and what was implemented in the repository.

---

## 1. Starting question

A coworker needs to run `zoom_daily_summary.py` and the Streamlit app on daily transcripts in Slack, ideally on a schedule (e.g. cron).

We investigated whether the repo could grant **programmatic Slack access** for that purpose.

---

## 2. Findings (initial state)

| Topic | Finding |
|-------|---------|
| Existing Slack integration | **None** in the repo before this work |
| Summary tools | `climate_streamlit/zoom_daily_summary.py` (CLI), `zoom_daily_summary_app.py` (Streamlit) |
| Input | Local file `meeting_saved_closed_caption.txt` (Zoom closed captions) |
| LLM | Local **Ollama** (`qwen2.5:7b-instruct` by default) |
| Prior manual workflow | Copy files from Mac (`~/Documents/Zoom`) to Slack by hand |

A meeting summary had already noted: *“automate collection of information, which requires obtaining a key from Slack.”*

---

## 3. Agreements

### 3.1 Where automation runs

| Agreement | Detail |
|-----------|--------|
| **Host machine** | Peter’s **Mac** — Zoom writes session folders locally |
| **Source directory** | `~/Documents/Zoom` (default; configurable) |
| **Not** Slack-as-input | We do **not** pull transcripts from Slack; Zoom files stay on disk |
| **Scheduler** | **launchd** (not cron) — better on macOS for user sessions |

### 3.2 What runs automatically

On each scheduled run:

1. **Discover** new session folders containing `meeting_saved_closed_caption.txt`
2. **Wait** until the transcript is stable (default: 10 minutes since last modification — Zoom may still be writing)
3. **Summarize** with Ollama (same logic as Streamlit: speaker aliases/regex, no anonymization)
4. **Save** `docs/summary/YYYY_MM_DD_HH_MM_summary.md`
5. **Upload to Slack** — summary plus session files (see §3.4)
6. **Track** processed transcripts in `config/zoom_daily_summary/processed_transcripts.json` (path + mtime)

If Slack upload fails after the summary exists, the **next run retries upload only** (no re-summarization).

### 3.3 launchd schedule (UTC)

Runs **every day** at these **UTC** times (plist uses `TimeZone: UTC`):

| UTC | UK (GMT) | UK (BST) |
|-----|----------|----------|
| 09:30 | 09:30 | 10:30 |
| 11:00 | 11:00 | 12:00 |
| 12:00 | 12:00 | 13:00 |
| 18:00 | 18:00 | 19:00 |

Install: `./scripts/install_zoom_daily_summary_launchd.sh`  
Uninstall: `./scripts/install_zoom_daily_summary_launchd.sh --uninstall`  
Logs: `/tmp/zoom_summary_watch.log`

**Constraint:** The Mac must be **awake and logged in** at those times; launchd does not run jobs while asleep.

### 3.4 Slack: post, not fetch

| Agreement | Detail |
|-----------|--------|
| **Slack role** | **Outbound only** — upload files to a channel after processing |
| **Coworker** | Does **not** need Slack API keys; she receives files in the channel |
| **Credentials** | One-time setup by workspace admin / Peter: Slack app + bot token |
| **Secrets file** | `config/zoom_daily_summary/slack.env` (gitignored) |
| **Optional settings** | `config/zoom_daily_summary/slack.json` (gitignored) |

#### `slack.env` (secrets)

Copy from `config/zoom_daily_summary/slack.env.example`:

```bash
SLACK_BOT_TOKEN=xoxb-...      # Bot User OAuth Token
SLACK_CHANNEL_ID=C...         # Target channel ID
ZOOM_SLACK_UPLOAD_ALL_SESSION_FILES=1   # 1 = all session files; 0 = summary + transcript only
ZOOM_SLACK_TIMEOUT_S=600      # HTTP timeout for large uploads (seconds)
```

The shell wrapper **sources** `slack.env` before calling Python.

#### Slack app requirements

- Scopes: `files:write`, `chat:write`
- Bot invited to the target channel (`/invite @YourBot`)

### 3.5 Upload all Zoom session files

| Agreement | Detail |
|-----------|--------|
| **Default** | Upload **every file** in the Zoom session folder (transcript, chat, audio, video, etc.) plus the generated summary |
| **Shell default** | `run_zoom_daily_summary_watch.sh` sets `ZOOM_SLACK_UPLOAD_ALL_SESSION_FILES=1` and passes `--slack-upload-all-session-files` |
| **Opt out** | Set `ZOOM_SLACK_UPLOAD_ALL_SESSION_FILES=0` or `"upload_all_session_files": false` in `slack.json` |
| **Size limit** | Skip files &gt; **1024 MB** (Slack limit); log reason |
| **Exclusions** | `.DS_Store`, `Thumbs.db`, `desktop.ini` (configurable in `slack.json`) |
| **Batching** | 10 files per Slack message (API fails above ~14) |

Typical session folder contents:

- `meeting_saved_closed_caption.txt`
- `chat.txt` (not used for summarization; still uploaded)
- `audio_only.m4a`, `*.mp4` (if recording enabled)

### 3.6 Manual / editorial workflow unchanged

| Tool | Use |
|------|-----|
| **Streamlit app** | Review and edit summary before sharing, when needed |
| **CLI** | One-off runs with `--input` |
| **Watch + launchd** | Unattended discover → summarize → Slack |

### 3.7 What we explicitly did not build

- Slack **ingestion** (reading transcripts from Slack)
- Cloud-hosted Ollama (still **localhost** unless changed)
- Coworker-side cron on her machine
- Automatic install of Ollama or Slack app (manual one-time setup)

---

## 4. Implemented components

| Path | Purpose |
|------|---------|
| `climate_streamlit/zoom_daily_summary_watch.py` | Discover sessions, summarize, state file, orchestrate Slack |
| `climate_streamlit/zoom_slack.py` | Slack file upload API (batch, size checks, session file collection) |
| `scripts/run_zoom_daily_summary_watch.sh` | launchd wrapper: `slack.env`, upload-all default, timeout |
| `scripts/install_zoom_daily_summary_launchd.sh` | Install/remove LaunchAgent |
| `config/launchd/com.chatbot.zoom-daily-summary.plist` | UTC schedule template (`__REPO_ROOT__` substituted on install) |
| `config/zoom_daily_summary/slack.env.example` | Secret template |
| `config/zoom_daily_summary/slack.json.example` | Channel ID, upload flags, excludes |
| `config/zoom_daily_summary/processed_transcripts.json` | Runtime state (created on first run) |
| `config/zoom_daily_summary/speaker_aliases.json` | Speaker name corrections (shared with Streamlit) |
| `tests/test_zoom_daily_summary_watch.py` | Watch/discovery tests |
| `tests/test_zoom_slack.py` | Slack collection/upload tests |

LaunchAgent runs: `run_zoom_daily_summary_watch.sh --require-slack` (fails loudly if `slack.env` missing).

---

## 5. Operator checklist

1. Ollama installed; `ollama serve` running; model pulled (`qwen2.5:7b-instruct`)
2. Python venv: `climate_streamlit/venv`
3. `cp config/zoom_daily_summary/slack.env.example → slack.env` and fill in token + channel
4. Optional: `slack.json` from example
5. Dry run: `./scripts/run_zoom_daily_summary_watch.sh --dry-run`
6. Install launchd: `./scripts/install_zoom_daily_summary_launchd.sh`
7. macOS **Full Disk Access** for shell/Terminal if `~/Documents/Zoom` is blocked

---

## 6. Open items (not agreed / not done)

- Posting a short “summary only” message in Slack without file attachments
- Separate channel per project
- `launchd` job to start Ollama at login
- Backfill upload for sessions summarized before Slack integration

---

## 7. Revision history

| Date | Change |
|------|--------|
| 2026-05-15 | Initial record: local watch, launchd UTC schedule, Slack outbound upload, all session files |

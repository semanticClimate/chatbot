# Serverless (local Windows/Mac) — installation outline

This document is a **plan only**: proposed scripts and procedures for naive users who run the Streamlit app on their own machine without a central server. No implementation scripts are included here yet.

**Assumptions:** the app runs locally; outbound HTTPS for Groq; local disk for `chroma_db/` and bundled `input/`; no centralized server operations.

---

## Goals for naive users

- Prefer **one clear path** (“do these steps”) over branching “if you already have…” prose hidden in the middle.
- **Detect or install** Python in a repeatable way without assuming Git.
- Avoid “open Terminal and paste five commands” unless there is **one** scripted entrypoint that does the rest.
- Separate **bootstrap** (install tooling + dependencies + first-run) from **daily launch** (double-click or one command).

---

## Proposed artifacts (scripts and helpers)

| Artifact | Audience | Purpose |
|----------|----------|---------|
| `install_windows.ps1` (or `.cmd` wrapper) | Windows | Python install guidance; creates venv; `pip install`; optional first-run sanity checks; prints next step |
| `install_mac.sh` (+ optional `.command` bundle) | macOS | Same as above using bash/zsh |
| `launch_streamlit.bat` / `Launch Climate Chatbot.command` | Naive users | Activates venv and runs `streamlit run app.py` without teaching shell paths |
| `check_environment.*` (small helper) | Support | Prints Python version, venv existence, pip, whether `GROQ_API_KEY` is set (masked), whether `input/` and HTML exist — for troubleshooting |
| `requirements.lock` or pinned export (later) | Reproducibility | Same dependency graph across machines — optional follow-up |

**Optional later tier (heavier engineering):**

| Artifact | Purpose |
|----------|---------|
| Packaged installer (e.g. PyInstaller, Briefcase, embedded Python distro) | True “no Python visible” installs |

---

## Installation procedure (conceptual phases)

### Phase A — Acquire the app (no Git assumed)

- Deliver a **ZIP** (or installer) containing `climate_streamlit/`, `input/`, and documentation placeholders; **`chroma_db/` omitted** (built on first run).
- User unpacks to a folder path **without spaces** where possible (reduces Windows path issues).

### Phase B — Runtime: Python

- **Track 1 — Python already installed (3.10+)**  
  Scripts verify version and **`python -m pip`** availability.
- **Track 2 — No Python**  
  Documentation and script messaging: install from **python.org** installers (Windows / macOS ARM as needed); on Windows emphasize “Add Python to PATH”. On macOS, official installer first; Homebrew as a **secondary** path to avoid unnecessary branching for beginners.

### Phase C — Dependencies

- Scripts run `python -m venv .venv` in a **single canonical location** (repo root or `climate_streamlit/` — choose one and document it consistently).
- `python -m pip install --upgrade pip`, then `pip install -r climate_streamlit/requirements.txt` and **`pymupdf`** per `climate_streamlit/README.md`.

### Phase D — Secrets

- Guided creation of `climate_streamlit/.streamlit/secrets.toml` **or** a small placeholder flow that reminds the user to set `GROQ_API_KEY`.
- Any automation around secrets should not hide risks: file permissions and plain-text storage on disk.

### Phase E — First launch

- Run `streamlit run app.py` from `climate_streamlit/`.
- Set expectations: **first run may be slow** (embeddings and Chroma build); firewall prompts may appear on macOS.

### Phase F — Subsequent use

- Double-click launcher or one script; optionally open the browser to `http://localhost:8501`.

---

## User-facing checklist (for eventual end-user doc)

1. Download and unzip the package.  
2. Run the **Install** script for your platform.  
3. Add the Groq API key where instructed.  
4. Run the **Launch** shortcut or script.  
5. If something fails, run **check_environment** or see “Common issues” in `climate_streamlit/README.md` (to be extended).

---

## Risks to document when scripts are written

- **PATH** on Windows after Python install (“python not recognized”).
- **Multiple Python installs** (Microsoft Store vs python.org); on Windows, prefer `py -3` where it helps.
- **Gatekeeper** on macOS for unsigned `.command` or scripts.
- **Outbound network** blocked (corporate proxy) affecting Groq and first-run model or cache downloads.
- **Disk usage** for Chroma and embedding-related caches.

---

## Out of scope for this naive serverless path (until expanded)

- SSO, centralized logging, systemd, reverse proxies.
- Multi-user concurrency (single-machine, single-session mental model is enough for most home installs).

---

## Open decisions before implementation

- **Venv location:** repository root versus inside `climate_streamlit/`.
- **Windows shell:** PowerShell-only versus CMD + batch fallback for broader compatibility.

When those are decided, implement the artifacts in the first table and align `climate_streamlit/README.md` with the chosen canonical path.

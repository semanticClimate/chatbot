# Installation architecture

How the chatbot should be provisioned across environments: what gets installed where, how configuration is layered, and what must persist across upgrades.

## Environments

| Tier | Typical use | Characteristics |
|------|-------------|-------------------|
| **Developer workstation** | Local iteration | Python venv, `streamlit run app.py`, local `chroma_db/`, secrets in `.streamlit/secrets.toml` or shell env |
| **Shared server / VM** | Team or classroom | One service user, systemd (or similar) supervision, reverse proxy + TLS, secrets from host env or vault |
| **Container** | Repeatable deploy | Image with app + deps; mount `input/` and `chroma_db/` as volumes; inject `GROQ_API_KEY` at runtime |
| **Managed PaaS** | Low-ops hosting | Must support long-running web process, writable disk for `chroma_db/`, and outbound HTTPS to Groq |

This repository does not ship Docker or Terraform; the patterns above are the natural fits for the current codebase.

## Installation layers

```mermaid
flowchart TB
  subgraph Layer0["0 — Host OS"]
    OS[Linux / macOS / Windows]
  end

  subgraph Layer1["1 — Python runtime"]
    Py[Python 3.10+ recommended 3.11 or 3.12]
    Venv[Virtual environment optional but recommended]
  end

  subgraph Layer2["2 — Python dependencies"]
    Req[pip install -r requirements.txt]
    MuPDF[pip install PyMuPDF for fitz import]
  end

  subgraph Layer3["3 — Application config"]
    Secrets[GROQ_API_KEY via env or Streamlit secrets]
    Paths[HTML_PATH / PDF_PATH / CHROMA_DIR if customized]
  end

  subgraph Layer4["4 — Data assets"]
    Input[input HTML and optional PDF]
    Index[chroma_db after first successful run]
  end

  OS --> Py --> Venv --> Req --> MuPDF
  Req --> Secrets
  Req --> Paths
  Secrets --> Input
  Paths --> Input
  Input --> Index
```

1. **Host**: OS with enough disk for models/index and outbound HTTPS.
2. **Python**: Match project expectation (see `climate_streamlit/README.md`); isolate with a venv.
3. **Dependencies**: `requirements.txt` plus **`pymupdf`** (explicit in README; required for PDF features).
4. **Configuration**: `GROQ_API_KEY` mandatory for LLM replies; paths only if defaults are wrong for your layout.
5. **Data**: place book assets under `input/`; allow first-run build of `chroma_db/`.

## Repository layout contract

Installations should preserve this mental model:

```text
chatbot/                         # ROOT_DIR — persistent volume root for prod
  climate_streamlit/
    app.py
    html_sectioning.py
    requirements.txt
    .streamlit/                  # config + secrets.toml (local dev); avoid committing secrets
  input/
    full_student_book.html       # required
    2025_10/climate_academy_book.pdf   # optional
  chroma_db/                     # created at runtime — back up if you rely on stable indices
```

Code resolves `ROOT_DIR` as the parent of `climate_streamlit/`, so the app expects `input/` and default `chroma_db/` beside `climate_streamlit/`, not inside it.

## Provisioning checklist

**One-time:**

- Install Python **3.10+** (3.11/3.12 recommended).
- Clone or copy this repository maintaining the layout above.
- Create a venv, upgrade `pip`, run `pip install -r requirements.txt` and `pip install pymupdf`.
- Obtain a Groq API key and configure `GROQ_API_KEY` (environment variable preferred for servers).

**Assets:**

- Ensure `input/full_student_book.html` exists.
- Optionally add the PDF path used by default or update `PDF_PATH`.

**First run:**

- From `climate_streamlit/`: `streamlit run app.py`.
- Expect **longer startup** while embeddings and Chroma indexing run; subsequent starts reuse `chroma_db/`.

## Persistence and backups

| Artifact | Persist? | Notes |
|----------|-----------|-------|
| `chroma_db/` | Yes | Rebuild by deleting folder; CPU cost on regenerate |
| `input/` | Yes | Source of truth for book content |
| `.streamlit/secrets.toml` | Optional | Prefer env-based secrets on shared hosts |
| Python venv / site-packages | Rebuild OK | Derived from `requirements.txt` |

## Upgrades

1. Pull or deploy new application code under `climate_streamlit/`.
2. Re-run dependency install against updated `requirements.txt`.
3. If chunking logic, collection name, or source HTML changes materially, **delete `chroma_db/`** (or rename collection in code) to avoid stale retrieval, then restart once.

## Operational command (baseline)

Production-like hosts usually wrap:

```bash
cd /path/to/chatbot/climate_streamlit
source .venv/bin/activate   # if using venv
export GROQ_API_KEY="..."   # or use service env file
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

Use your platform’s equivalent for binding address, TLS (often via reverse proxy), logging, and restart policy.

For day-to-day developer setup, follow `climate_streamlit/README.md` step by step.

## Smoke testing: FastAPI + web client (1–2 users, non-production)

Use this when you only need lightweight verification with yourself or one other tester. No subscription or long-lived cloud host is required unless you choose one.

### Local smoke (recommended)

1. **Prep once**  
   - Clone repo, activate venv, `pip install -r requirements.txt` from repo root.  
   - Ensure `input/` book assets and `chroma_db/` behavior match `climate_streamlit/Getting_started.md`.

2. **Run API locally**  
   - `export GROQ_API_KEY='…'` in the **same** terminal as the server; confirm with `printenv GROQ_API_KEY`.  
   - From repo root: `python -m uvicorn fastapi_app.main:app --host 127.0.0.1 --port 8800`  
   - Prefer `python -m uvicorn` over bare `uvicorn` if `which uvicorn` points at an older Python (e.g. missing `tomllib`).

3. **Run web UI locally**  
   - `cd frontend` → `python -m http.server 8081`.  
   - Browser: `http://127.0.0.1:8081`, set API base to `http://127.0.0.1:8800`.  
   - If the browser blocks requests: `export CLIMATE_API_CORS_ORIGINS=http://127.0.0.1:8081` and restart the API.

4. **Smoke**  
   - Ask a question; citation chips should populate the sources pane.  
   - Optional: `curl http://127.0.0.1:8800/health`, `/ready`, and `POST /ask` with JSON body.

5. **Share with one other tester (optional)**  
   - Same LAN: they use your machine IP for UI and API base; widen CORS to match that origin.  
   - Off-LAN: use a tunnel (e.g. ngrok, Cloudflare Tunnel, Tailscale) to the **API**; set API base URL in the UI; set **CORS** to the tunnel or UI origin.  
   - Do not commit the Groq key; it stays only on the API host / your shell.
   - For a full Cloudflare Tunnel walkthrough, see [`docs/installation/cloudflare-tunnel-testing.md`](./cloudflare-tunnel-testing.md).

6. **Version control**  
   - Commit from a clean branch; tag or document which revision includes `fastapi_app/` and `frontend/` if others will reproduce.

### GitHub Pages (static UI only, optional later)

1. Enable GitHub Pages on the repo (e.g. publish `frontend/` or `docs/` per GitHub settings).  
2. Host **FastAPI elsewhere** with **HTTPS** (Pages is HTTPS; mixed `http` API calls are blocked).  
3. Set **CORS** on the API to your Pages origin.  
4. Configure or document the **HTTPS API base URL** in the deployed client (no secrets in the repo).

### If you skip cloud entirely

Complete **Local smoke** steps 1–4 only; no PaaS subscription required.

# chatbot

Climate Academy / IPCC grounded chat: **FastAPI backend** + static **`frontend/`** browser UI.

## Running the API + frontend (quick reference)

Dependencies are listed in the repo-root [`requirements.txt`](requirements.txt). Use a **Python 3.11+** venv for the API.

**Terminal A — API (needs `GROQ_API_KEY`; do not commit the key)**

```bash
cd /path/to/chatbot
source .venv/bin/activate
export GROQ_API_KEY='gsk_…'   # verify with: printenv GROQ_API_KEY

# Optional: switch source document (default: cabook)
export CLIMATE_CORPUS_PROFILE=cabook      # Climate Academy Student Book
# export CLIMATE_CORPUS_PROFILE=ipcc_syr   # IPCC AR6 SYR Longer Report

python -m uvicorn fastapi_app.main:app --host 127.0.0.1 --port 8800
```

Use `python -m uvicorn`, not necessarily bare `uvicorn`, if your shell’s `uvicorn` points at an older Python (e.g. 3.8 without `tomllib`).

**Terminal B — frontend (no API key)**

```bash
cd /path/to/chatbot/frontend
python -m http.server 8081
```

Open `http://127.0.0.1:8081` and set the API base URL to `http://127.0.0.1:8800`. If the browser blocks cross-origin requests, start Terminal A with e.g. `export CLIMATE_API_CORS_ORIGINS=http://127.0.0.1:8081`.

**Smoke checks**

```bash
curl -s http://127.0.0.1:8800/health
curl -s http://127.0.0.1:8800/ready
curl -s http://127.0.0.1:8800/corpus
```

More detail: [`frontend/README.md`](frontend/README.md), [`docs/client-server-architecture.md`](docs/client-server-architecture.md).

**Frontend (layout & content):** start at [`docs/web-client-guidelines.md`](docs/web-client-guidelines.md). **Issues / bugs / features:** [github.com/semanticclimate/chatbot/issues](https://github.com/semanticclimate/chatbot/issues).

---

## Source documents (corpus profiles)

Corpus paths, Chroma collection names, UI copy, and system prompts are defined per profile in [`climate_streamlit/config/app.defaults.toml`](climate_streamlit/config/app.defaults.toml).

| Profile | Document | HTML path |
|---------|----------|-----------|
| `cabook` (default) | Climate Academy Student Book | `input/full_student_book.html` |
| `ipcc_syr` | IPCC AR6 SYR Longer Report | `../amilib/test/resources/ipcc/syr/longer-report/html_with_ids.html` |

Select at API startup:

```bash
export CLIMATE_CORPUS_PROFILE=ipcc_syr
```

Each profile uses its own Chroma directory (`chroma_db` vs `chroma_db_ipcc_syr`). Restart the API after changing profile. Override the config file with `CLIMATE_CONFIG_PATH=/path/to/custom.toml`.

---

## Architecture

| Layer | Location |
|-------|----------|
| **Frontend** | `frontend/` — static HTML/CSS/JS |
| **API** | `fastapi_app/main.py` → `climate_streamlit/api_server.py` |
| **RAG / config** | `climate_streamlit/` (shared Python package) |

Legacy Streamlit UI (`climate_streamlit/app.py`) is optional and not used for deployment; see [`climate_streamlit/Getting_started.md`](climate_streamlit/Getting_started.md) if needed.

---

## Fixing chroma-hnswlib build error on macOS

Your failure is happening while installing chromadb’s dependency chroma-hnswlib, and the log shows:

“You have not agreed to the Xcode license agreements…”
and then “Unsupported compiler -- at least C++11 support is needed!”

Do this:

Accept the Xcode license + ensure compiler tools exist:

```bash
sudo xcodebuild -license
xcode-select --install
```

Retry dependency install in the activated venv:

```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

If it still can’t build wheels, switch to Python 3.11+ on macOS/arm64, recreate the venv, and reinstall.

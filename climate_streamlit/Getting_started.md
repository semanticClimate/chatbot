# Climate Streamlit Chatbot

A Streamlit-based Climate Academy chatbot with:
- semantic search over the book content (ChromaDB + local ONNX embeddings)
- grounded answers with source links
- Groq LLM responses (`llama-3.3-70b-versatile`)

## 1) Prerequisites

Install these first:
- Python 3.10+ (3.11/3.12 recommended)
- Git (optional, for cloning)
- A free Groq API key from [console.groq.com](https://console.groq.com)

## 2) Project Layout (expected)

This app expects this structure:

```text
chatbot/
  fastapi_app/
    main.py
    requirements.txt
  climate_streamlit/
    streamlit_app/
      app.py
      requirements.txt
    .streamlit/
      secrets.toml
  requirements.txt
  input/
    full_student_book.html
    2025_10/
      climate_academy_book.pdf
  chroma_db/
```

Important:
- `app.py` reads the HTML from: `../input/full_student_book.html`
- `app.py` optionally reads the PDF from: `../input/2025_10/climate_academy_book.pdf`

## 3) Setup

From the repository root (`chatbot`), run:

### Step 2 — Add key to secrets.toml

(Only needed if `GROQ_API_KEY` is not set as an environment variable — recommended)

Edit `.streamlit/secrets.toml`:

```toml
GROQ_API_KEY = "gsk_...your_key_here"
```

### Windows (PowerShell)

```powershell
cd <path-to-your-project>\chatbot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r streamlit_app/requirements.txt
```

### macOS / Linux

```bash
cd /path/to/your/project/chatbot
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r streamlit_app/requirements.txt
```

For API-only setup instead:

```bash
pip install -r fastapi_app/requirements.txt
```

## 4) Add your Groq API key

Create/edit this file:
- `climate_streamlit/.streamlit/secrets.toml`

Add:

```toml
GROQ_API_KEY = "gsk_your_key_here"
```

The app also supports `GROQ_API_KEY` from environment variables, but `secrets.toml` is the easiest.

## 5) Ensure input files exist

Required:
- `input/full_student_book.html`

Optional but recommended:
- `input/2025_10/climate_academy_book.pdf`

If your files are in different locations, update `HTML_PATH` and `PDF_PATH` in `app.py`.

## 6) Run the app

From repo root (`chatbot/`):

```bash
streamlit run climate_streamlit/streamlit_app/app.py
```

Then open:
- [http://localhost:8501](http://localhost:8501)

### Optional: FastAPI RAG sidecar (lightweight server)

Use this when you want embeddings + Groq behind a small REST service while Streamlit stays as the UI. The API loads `config/app.defaults.toml`, shares the same `../chroma_db` and `../input/` paths as the single-process app, and does not keep per-user chat state between requests.

**Terminal A — API** (from repo root with the same virtualenv):

```bash
export GROQ_API_KEY="gsk_..."
uvicorn fastapi_app.main:app --host 127.0.0.1 --port 8800
```

Smoke checks:

```bash
curl -s http://127.0.0.1:8800/health
curl -s http://127.0.0.1:8800/ready
```

**Terminal B — Streamlit** (book HTML/PDF still read locally; RAG goes to the API):

```bash
export CLIMATE_API_BASE_URL="http://127.0.0.1:8800"
streamlit run climate_streamlit/streamlit_app/app.py
```

Useful environment variables:

| Variable | Purpose |
|----------|---------|
| `CLIMATE_API_BASE_URL` | Base URL of the FastAPI app; when set, Streamlit skips local Chroma/Groq for answers. |
| `CLIMATE_API_PORT` | Port when starting via `python fastapi_app/main.py` (default `8800`). |
| `CLIMATE_API_HOST` | Bind address for `python fastapi_app/main.py` (default `0.0.0.0`). |
| `CLIMATE_API_CORS_ORIGINS` | Comma-separated allowed origins, or `*`, for browsers calling the API directly. |

REST surface (JSON): `POST /ask`, `POST /retrieve`, `GET /health`, `GET /ready`, `GET /book/jump`, `POST /conversation/import`, `POST /conversation/import_csv`, `POST /conversation/export`.

## 7) First run behavior

On first run, the app builds embeddings and indexes chunks into `../chroma_db`.
This can take a little time depending on machine speed.

Later runs are much faster because it reuses the saved vector DB.

## 8) Reset / rebuild the vector database

If you change the source HTML and want a full re-index, delete `chroma_db` and run again.

### Windows
```powershell
cd <path-to-your-project>\chatbot
Remove-Item -Recurse -Force .\chroma_db
```

### macOS / Linux
```bash
cd /path/to/your/project/chatbot
rm -rf ./chroma_db
```

## 9) Common issues

- `GROQ_API_KEY not set`
  - Confirm `climate_streamlit/.streamlit/secrets.toml` exists and contains `GROQ_API_KEY`.

- `HTML book not found`
  - Confirm `input/full_student_book.html` exists, or update `HTML_PATH` in `app.py`.

- Import error for `fitz`
  - Run `pip install pymupdf` in your active virtual environment.

- Rate limit / temporary Groq errors
  - Wait briefly and retry.

## 10) Run again later

### Windows
```powershell
cd <path-to-your-project>\chatbot
.\.venv\Scripts\Activate.ps1
streamlit run climate_streamlit/streamlit_app/app.py
```

### macOS / Linux
```bash
cd /path/to/your/project/chatbot
source .venv/bin/activate
streamlit run climate_streamlit/streamlit_app/app.py
```

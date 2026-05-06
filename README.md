# chatbot

## Running the RAG API + browser client (quick reference)

Dependencies are listed in the repo-root [`requirements.txt`](requirements.txt). Use a **Python 3.11+** venv for the API.

**Terminal A — API (needs `GROQ_API_KEY`; do not commit the key)**

```bash
cd /path/to/chatbot
source .venv/bin/activate
export GROQ_API_KEY='gsk_…'   # must be exported; verify with: printenv GROQ_API_KEY

python -m uvicorn fastapi_app.main:app --host 127.0.0.1 --port 8800
```

Use `python -m uvicorn`, not necessarily bare `uvicorn`, if your shell’s `uvicorn` points at an older Python (e.g. 3.8 without `tomllib`).

**Terminal B — static web UI (no API key)**

```bash
cd /path/to/chatbot/web_client
python -m http.server 8080
```

Open `http://127.0.0.1:8080` and set the API base URL to `http://127.0.0.1:8800`. If the browser blocks cross-origin requests, start Terminal A with e.g. `export CLIMATE_API_CORS_ORIGINS=http://127.0.0.1:8080`.

**Smoke checks**

```bash
curl -s http://127.0.0.1:8800/health
curl -s http://127.0.0.1:8800/ready
```

More detail: [`web_client/README.md`](web_client/README.md), [`climate_streamlit/Getting_started.md`](climate_streamlit/Getting_started.md) for Streamlit.

---

## How climate_streamlit/app.py works
It’s a Streamlit app that does a simple RAG (Retrieval-Augmented Generation) loop:

UI (Streamlit)

Sets the page title/layout and defines some inline CSS for the chat bubbles.
Keeps chat history in st.session_state.messages.
Sidebar lets you pick a language (English/Hindi/French) and click example questions.
“Clear chat” empties st.session_state.messages and reruns.
Cached resources (runs once, then reused)

load_embedder() loads a local embedding model: all-MiniLM-L6-v2 using sentence-transformers.
load_groq() creates a Groq(...) client using GROQ_API_KEY from either:
environment variable GROQ_API_KEY, or
Streamlit secrets: st.secrets["GROQ_API_KEY"]
If the key is missing, it shows an error and stops the app.
Build / load the vector database (first run vs later runs)

build_knowledge_base() uses chromadb.PersistentClient(path=CHROMA_DIR) with CHROMA_DIR = "./chroma_db".
It checks collection.count(). If the DB already has chunks, it skips re-embedding.
Otherwise it:
extracts text from ClimateAcademy_Book.pdf using pdfplumber,
chunks the text (with overlap) into pieces of about CHUNK_SIZE=400 words and CHUNK_OVERLAP=60,
embeds each chunk with the local embedding model,
stores (documents, embeddings) into ChromaDB.
Chat loop (retrieve → answer)

## When you ask a question:
retrieve() embeds your question, queries ChromaDB for top TOP_K=5 chunks, and filters by distance (d < 1.5).
ask_groq() builds a prompt:
system message = rules + --- retrieved passages --- {context}
then appends the last 10 conversation turns
sends it to Groq (GROQ_MODEL = "llama-3.3-70b-versatile") and returns the assistant text.
The assistant response is appended to st.session_state.messages and rendered.


## How to run it (Streamlit)

For paths, book assets under `input/`, and current entrypoints, see [`climate_streamlit/Getting_started.md`](climate_streamlit/Getting_started.md).

From repo root, install deps:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Groq key: environment variable `GROQ_API_KEY` and/or `climate_streamlit/.streamlit/secrets.toml` per that guide.

Example (adjust if your Streamlit entrypoint differs):

```bash
cd climate_streamlit
streamlit run app.py
```

Then open http://localhost:8501 . First run may build `chroma_db/` at the repo root; later runs reuse it.

Fixing your chroma-hnswlib build error on macOS
Your failure is happening while installing chromadb’s dependency chroma-hnswlib, and the log shows:

“You have not agreed to the Xcode license agreements…”
and then “Unsupported compiler -- at least C++11 support is needed!”
Do this:

Accept the Xcode license + ensure compiler tools exist:

sudo xcodebuild -license
(also usually necessary) xcode-select --install
Retry dependency install in the activated venv:

pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
If it still can’t build wheels, the next most common cause is no wheel available for your Python version/architecture. In that case, switch to a Python version that has better wheel coverage (often Python 3.11 on macOS/arm64), recreate the venv, and reinstall.

If you tell me your python --version (inside the venv) and whether you’re on Apple Silicon (arm64), I can suggest the most likely “pin/change” to make chromadb install cleanly.
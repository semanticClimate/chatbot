# Climate Academy Chatbot — Streamlit + Groq

Multilingual climate chatbot. The Streamlit UI is one file; the book is **structured HTML** with nested `<section>` elements and automatic **§ decimal numbering** for citations. (Inline CSS only for chat styling.)

---

## Stack — everything is free

| Layer           | Tool                                  | Cost              |
|-----------------|---------------------------------------|-------------------|
| UI              | Streamlit                             | Free              |
| Book format     | HTML + BeautifulSoup (nested sections)| Free              |
| Embeddings      | sentence-transformers (local)         | Free — no API key |
| Vector database | ChromaDB (saved on disk)              | Free              |
| LLM             | Groq API (llama-3.3-70b-versatile)    | Free tier         |

---

## Project structure

```text
chatbot/
├── climate_streamlit/
│   ├── app.py
│   ├── html_sectioning.py
│   ├── requirements.txt
│   └── .streamlit/secrets.toml
├── input/
│   ├── sample_ca_book.html
│   └── climate_academy_book.pdf
├── docs/HTML_SECTION_NESTING.md
├── tests/test_html_sectioning.py
└── chroma_db/
```

---

## Setup — step by step

### Step 1 — Get your free Groq API key
1. Go to https://console.groq.com
2. Sign up free — no credit card needed
3. Click **API Keys** → **Create API Key**
4. Copy the key (starts with `gsk_...`)

### Step 2 — Add key to secrets.toml

(Only needed if "GROQ_API_KEY" is not set as environment variable (recommended))

Edit `.streamlit/secrets.toml`:
```toml
GROQ_API_KEY = "gsk_...your_key_here"
```

### Step 3 — Create virtual environment (recommended)

**Mac / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```powershell
python -m venv venv
venv\Scripts\activate
```

### Step 4 — Install packages
```bash
pip install -r requirements.txt
```

### Step 5 — HTML files
The repository includes a subset sample at `input/sample_ca_book.html`.  
When you locate the full HTML export, place it in `input/` and update `HTML_PATH` in `app.py`.

**Switched from the old PDF pipeline?** Remove the old vector store so chunks rebuild:

```bash
rm -rf ../chroma_db
```

### Step 6 — Run
```bash
streamlit run app.py
```

Browser opens automatically at `http://localhost:8501`

---

## First run vs every run after

**First run (~2 minutes):**
```
📄 Parsing HTML book ...
🔄 Embedding chunks... 10%
🔄 Embedding chunks... 45%
🔄 Embedding chunks... 100%
✅ Knowledge base ready — 912 chunks indexed!
```

**Every run after (instant — loads from disk):**
```
✅ ChromaDB already has 912 chunks — skipping re-embedding.
```

---

## How it works

```
User asks a question
        ↓
Embed question → vector numbers (free local model)
        ↓
ChromaDB finds top 5 most similar chunks (semantic search); each chunk is tagged with **§ section number**
        ↓
System prompt = rules + retrieved chunks (passages show § x.y.z — title)
        ↓
Groq API (llama-3.3-70b) reads chunks → answers in user's language **with § citations**
        ↓
Answer shown in chat
```

---

## Languages supported
- English → click EN or type in English
- Hindi → click हि or type in Hindi
- French → click FR or type in French
- Any other language → Groq auto-detects and replies in it

---

## Groq free tier limits

| Limit | Value |
|---|---|
| Requests per minute | 30 |
| Requests per day | 1,000 |
| Tokens per minute | 6,000 |

More than enough for a student chatbot.

---

## Common errors and fixes

| Error | Cause | Fix |
|---|---|---|
| `GROQ_API_KEY not set` | secrets.toml missing or wrong path | check `.streamlit/secrets.toml` location |
| `rate_limit` | too many requests | wait 1 minute and try again |
| `invalid_api_key` | wrong key | check key at console.groq.com |
| `proxies` error | groq/httpx version conflict | run `pip install groq httpx==0.27.0` |
| ChromaDB telemetry warnings | known ChromaDB bug | harmless, add `os.environ["ANONYMIZED_TELEMETRY"]="False"` at top of app.py |

---

## Reset knowledge base
To rebuild ChromaDB (e.g. if you change the HTML book):
```bash
# Mac / Linux
rm -rf ../chroma_db

# Windows
rmdir /s /q ..\chroma_db
```
Then run `streamlit run app.py` again.

---

## Every time you come back to work on it

```bash
# Mac / Linux
cd /path/to/climate_streamlit
source venv/bin/activate
streamlit run app.py

# Windows
cd D:\climate_streamlit
venv\Scripts\activate
streamlit run app.py
```

---

## Deploy to Streamlit Cloud (free public hosting)
1. Push your code to a GitHub repo
2. Go to https://share.streamlit.io
3. Connect your repo
4. Add `GROQ_API_KEY` in the Secrets section (same format as secrets.toml)
5. Deploy — your chatbot gets a public URL anyone can access

> Note: Do not commit private book files from `input/` and `chroma_db/` to GitHub
> if the book content is private.

---

## Health check
Open in browser after running:
```
http://localhost:8501
```
Sidebar shows:
- LLM: Llama 3.3 70B via Groq (free)
- Embeddings: all-MiniLM-L6-v2 (local)
- Vector DB: ChromaDB
- Total chunks indexed

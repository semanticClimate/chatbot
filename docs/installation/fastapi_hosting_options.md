# FastAPI hosting options (lightweight and free)

**Date:** 2026-05-29

This note compares **lightweight, low-cost or free** ways to host the Climate Academy chatbot when the architecture is:

- **FastAPI** (`uvicorn`) — REST API (chat, retrieve, health)
- **Separate web client** — static HTML/JS; calls the API over HTTPS
- **On the server** — ChromaDB index, book HTML under `input/`, local embeddings (`sentence-transformers`)
- **External** — Groq for answer generation (`GROQ_API_KEY`)

The Streamlit app in `climate_streamlit/` is a separate deployment path; this document is for the **API + client** stack only.

---

## Architecture

```
Browser  →  static files (nginx / CDN / same VM)
         →  FastAPI (/api/chat, /health, …)
                →  Chroma + local embeddings
                →  Groq
```

Groq stays cloud-hosted. Hosting cost is mostly **RAM, disk, and always-on CPU** for the API process.

---

## What to optimize for

| Requirement | Why it matters |
|-------------|----------------|
| **~1–2 GB RAM** (ideally) | Embedding model + Chroma + `uvicorn` are tight on 512 MB |
| **Persistent disk** (or pre-built index in the image) | `chroma_db/` and `input/`; cold rebuild is slow |
| **Secret for `GROQ_API_KEY`** | Env or platform secrets — never in the image or repo |
| **HTTPS + CORS** | Frontend origin allowed; restrict public API if the book is private |
| **Single long-lived process** | Load embedder + Chroma at startup (`lifespan`); avoid serverless-only unless the vector DB is external |

---

## Good fits (lightweight and free)

### 1. Small VPS — Oracle Always Free, AWS/GCP free tier, university server

**Best fit for a real API and a private book.**

- Run `uvicorn` behind **nginx** (API) plus nginx or Caddy for static `dist/`.
- Use a volume for `chroma_db/` and `input/`.
- **Pros:** Full control, CORS, auth, logs, always-on, index stays on your infrastructure.
- **Cons:** You maintain OS, TLS, and updates.
- **Note:** 1 GB instances (e.g. AWS `t2.micro`) are usually **too small**; prefer **2 GB+** for embeddings + Chroma.

### 2. Fly.io / Render / Koyeb — container plus optional volume

**Good if you ship a `Dockerfile` with the API and optional baked index.**

- **Pros:** Standard container deploy; Fly volumes for `chroma_db`; health checks map to FastAPI `/health`.
- **Cons:** Free tiers: low RAM, sleep when idle (Render), cold starts; first deploy may OOM during index build.
- **Pattern:** Build Chroma in CI or locally, upload volume or bake into image; use **one** `uvicorn` worker on free tier.

### 3. Railway and similar (trial credits)

Same container pattern as above, but usually **not** a durable free tier — fine for short demos.

### 4. Cloudflare Tunnel — API on a machine you already have

**Not cloud hosting; exposes local FastAPI.**

- **Pros:** Free HTTPS URL to `localhost:8000`; book and DB never leave your Mac or lab machine.
- **Cons:** Host must be on; not production-grade for a team unless that machine is reliable.
- **Pattern:** `uvicorn` locally + tunnel; static site on the same host or GitHub Pages (configure CORS carefully).

### 5. Static frontend free + API elsewhere

Natural split for FastAPI:

| Frontend | API |
|----------|-----|
| GitHub Pages / Cloudflare Pages (free) | VPS or Fly |
| Same nginx on one VM (simplest CORS) | One origin: `/` static, `/api` proxied |

Keep `GROQ_API_KEY` **only** on the API server.

### 6. Google Cloud Run / AWS Lambda

**Possible but a poor default for this stack.**

- **Pros:** Pay-per-request free tier.
- **Cons:** Cold starts, large ML dependencies, Chroma wants local disk unless you move to a hosted vector DB.
- **Use when:** You later split a thin API from **managed** embeddings or vector storage.

---

## Usually a poor match

| Option | Issue |
|--------|--------|
| **Streamlit Cloud** | Hosts Streamlit apps, not a standalone FastAPI service |
| **PythonAnywhere free** | Tight RAM/time limits; heavy `chromadb` + `sentence-transformers` often painful |
| **Serverless-only, no volume** | Rebuild index every cold start; awkward dependency size |
| **512 MB VM with many `uvicorn` workers** | OOM; use **one worker** and shared startup-loaded models |

---

## FastAPI deployment notes

- **Process model:** One worker on free tiers; load embedder and Chroma once in `lifespan` / startup.
- **Endpoints (example):** `POST /api/chat`, `GET /health`, optional `POST /api/retrieve` for debugging — matches a separate web client and optional analytics.
- **Auth:** For a private book, add API key or session auth before a public URL; the API is directly callable unlike a bundled Streamlit server.
- **Analytics (CSV):** Log on the server or write to disk on the VM; fits a VPS better than ephemeral serverless disks.

Example nginx split on one host:

```nginx
# Static client
location / {
    root /var/www/climate-client;
    try_files $uri $uri/ /index.html;
}

# API
location /api/ {
    proxy_pass http://127.0.0.1:8000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

Run locally before deploy:

```bash
uvicorn your_app:app --host 0.0.0.0 --port 8000
```

---

## Practical recommendation

| Goal | Suggestion |
|------|------------|
| **Private book, stable team URL** | Small **VPS** (Oracle free or institutional server): nginx + FastAPI + static client, persistent `chroma_db`. |
| **Quick external demo** | **Fly.io** or **Render** with Docker, pre-built index, one worker, platform secrets for Groq. |
| **Demo before a VM exists** | **Cloudflare Tunnel** to a dev machine running `uvicorn`. |
| **Long term, minimal ops** | Stay on a **single VM** until you need Cloud Run (or similar) plus a hosted vector DB. |

---

## Compared to Streamlit hosting

Streamlit Community Cloud is one-click for UI and backend together. With FastAPI you deploy **at least two concerns** (API + static client), but you get a **standard REST surface**, clearer CORS and auth, and generic **Python container or VM** hosting — not tied to Streamlit’s platform or RAM limits.

When the FastAPI app exists in this repo, reuse the same RAG building blocks as `climate_streamlit/app.py` (`html_sectioning`, Chroma paths, Groq client) behind startup-loaded singletons and thin route handlers.

---

## Related code and docs

- `climate_streamlit/app.py` — current RAG logic (reference for a future FastAPI port)
- `climate_streamlit/html_sectioning.py` — HTML chunking and section numbering
- [../climate-academy-assistant-explained.md](../climate-academy-assistant-explained.md) — colleague-facing overview
- [../project_review_2026_04_25.md](../project_review_2026_04_25.md) — architecture summary

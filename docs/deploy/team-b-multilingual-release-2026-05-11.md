# Team B handoff — multilingual chat revision (2026-05-11)

This revision restores **language-matched answers** end-to-end for the **FastAPI + web client** stack used in tunnel demos, adds **Portuguese** and **Spanish** alongside **English / Hindi / French**, and surfaces **sample questions per language** in the browser UI.

---

## What changed

| Area | Change |
|------|--------|
| **LLM system prompt** | Stronger rules: detect user language each turn; translate faithfully from English sources without extra facts; explicit support for EN, HI, FR, PT, ES (plus other languages the user writes). Files: `backend.app/prompts/system_rag_json.txt`, mirrored in legacy `backend.app/app.py`. |
| **Web client** | New `web_client/js/examples.js`: sample questions and empty-thread hints in five languages. Wired in `index.html`, `main.js`, `render.js`; styles in `css/components.css`. |
| **API UX** | `GET /` on the API host returns a short HTML page explaining that this URL is the API, not the chat UI (helps Cloudflare tunnel confusion). `backend.app/api_server.py`. |

---

## Deploy checklist (Team A → Team B)

### 1. Backend (FastAPI)

From repo root, same process as today:

- Ensure `GROQ_API_KEY` is set and `chroma_db` paths match your environment.
- Restart the API process after deploy so the prompt file is re-read (template load is cached in-process).

```bash
# Example
python -m uvicorn fastapi_app.main:app --host 0.0.0.0 --port 8800
```

- Confirm: `https://<api-host>/health` and `https://<api-host>/ready` OK.
- Optional: open `https://<api-host>/` in a browser — you should see the “API server, not chat page” message.

### 2. Web client (static assets)

Ship the **whole** `web_client/` directory (or your static host equivalent) so Team B gets:

- `js/examples.js` (**new**)
- Updated `js/main.js`, `js/render.js`, `index.html`, `css/components.css`

Serve over HTTP(S) as today; ES modules must not be opened as `file://`.

- In the UI, set **API base URL** to Team B’s API tunnel or origin.
- Ensure CORS remains correct: `CLIMATE_API_CORS_ORIGINS` includes the web origin (or `*` for dev only).

### 3. Smoke test (Team B)

1. Open the web client, point API at the new backend.
2. Click a **Français** or **Español** sample question → send.
3. Expect an answer **in that language**, with citation chips; book remains English.
4. Optionally try **हिन्दी** sample text.

---

## Operational note

Retrieval still uses the existing English-oriented embedding model: some non-English questions may retrieve slightly fewer relevant chunks than English. Model behavior for **answer language** is what this release tightens; improving **cross-lingual retrieval** would be a separate follow-up (e.g. multilingual embeddings or query translation).

---

## Files touched in this release

- `backend.app/prompts/system_rag_json.txt`
- `backend.app/app.py` (duplicate system prompt for monolithic Streamlit path)
- `backend.app/api_server.py` (`GET /` landing)
- `web_client/js/examples.js` (new)
- `web_client/js/main.js`
- `web_client/js/render.js`
- `web_client/index.html`
- `web_client/css/components.css`

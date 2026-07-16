# ⚠️ Do not merge this branch into `main`

This branch contains the refactored application structure. **Do not merge it into `main` yet** unless the old layout has been fully retired and the runtime paths, endpoints, and regression checks have all been verified.

## Chatbot_V1 (Refactored Architecture)

This repository contains the refactored version of the climate chatbot project.  
The codebase has been reorganized into a cleaner layered structure with separate backend, frontend, data, and test areas.

### Project overview

The refactor separates responsibilities that were previously mixed inside the `climate_streamlit` package.

Current high-level layout:

- `backend/` — FastAPI application, API routes, RAG, LLM, services, config, database, utilities
- `frontend/` — static web client, CSS, JavaScript, assets
- `data/` — ChromaDB, input files, encyclopedia sources, media
- `tests/` — automated tests
- `docs/` — technical documentation and reports

---

## What changed in the refactor

### Original layout
The earlier project centered around a large `climate_streamlit` package that held:
- Streamlit app logic
- FastAPI server code
- API client code
- retrieval pipeline code
- LLM utilities
- PDF helpers
- UI helpers
- configuration and database access

### Refactored layout
The refactored version splits those responsibilities into clearer modules:

- backend startup lives in `backend/app/main.py`
- API handlers live in `backend/app/api/`
- orchestration logic lives in `backend/app/services/`
- retrieval logic lives in `backend/app/rag/`
- model interaction lives in `backend/app/llm/`
- PDF helpers live in `backend/app/pdf/`
- configuration lives in `backend/app/config/`
- database helpers live in `backend/app/database/`
- frontend JavaScript is split into modules inside `frontend/js/`

---

## Requirements

- Python 3.11+ recommended
- A virtual environment
- Required Python dependencies from `requirements.txt`
- A working `.env` or equivalent environment configuration if your local setup needs API keys

---

## How to run the backend

From the project root:

```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8800
```

This starts the FastAPI backend on:

- `http://127.0.0.1:8800`

Backend responsibilities include:
- serving API endpoints
- loading settings
- initializing the knowledge base
- handling retrieval and completion requests
- serving book and encyclopedia routes

---

## How to run the frontend

From the project root:

```powershell
python -m http.server 8081 --directory frontend
```

This serves the static frontend on:

- `http://127.0.0.1:8081`

The frontend connects to the backend API and provides:
- the chat interface
- sidebar actions
- book and encyclopedia panels
- modals and helper UI
- client-side state and rendering

---

## Typical local workflow

Open two terminals:

### Terminal 1 — backend
```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8800
```

### Terminal 2 — frontend
```powershell
python -m http.server 8081 --directory frontend
```

Then open the frontend in a browser and make sure it is pointed at the backend API base URL if your UI requires manual selection.

---

## Important notes

### Encyclopedia regression
During integration testing, an encyclopedia display regression was observed after the refactor. The most likely cause is a path/configuration mismatch introduced when runtime data was reorganized under `data/`.

### Path-sensitive areas
If something breaks after moving files, inspect:
- `backend/app/config/settings.py`
- `backend/app/rag/encyclopedia_document.py`
- `backend/app/rag/indexing.py`
- `backend/app/main.py`

These areas are most likely to be affected by directory changes.

---

## Documentation

Recommended technical docs:

- `docs/codebase_rectro.md`
- `docs/backend.md`
- `docs/frontend.md`

If you are new to the codebase, start with:
1. [backend.md](https://github.com/semanticClimate/chatbot/blob/refactored/docs/backend.md)
2. [frontend.md](https://github.com/semanticClimate/chatbot/blob/refactored/docs/frontend.md)
3. [codebase_rectro.md](https://github.com/semanticClimate/chatbot/blob/refactored/docs/codebase_rectro.md)

---

## Folder structure

```text
Chatbot_V1/
├── backend/
├── frontend/
├── data/
├── docs/
├── tests/
├── requirements.txt
└── README.md
```

---

## Short summary

This project is a refactored climate chatbot codebase with a cleaner separation between:
- server-side logic
- browser-side UI
- runtime data
- automated tests
- documentation

The structure is intentionally more modular so it is easier to maintain, debug, and extend.

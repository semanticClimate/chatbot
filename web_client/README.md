# Climate chat — vanilla web client

Static HTML/CSS/JS that talks to the FastAPI backend (`POST /ask`). ES modules must be served over HTTP (not `file://`).

## Run locally

From repo root:

```bash
cd web_client
python -m http.server 8081
```

Open http://127.0.0.1:8081 — set **API base URL** to `http://127.0.0.1:8800` (or your deployed URL).

Ensure the API allows this origin (e.g. `CLIMATE_API_CORS_ORIGINS=http://127.0.0.1:8081` or `*` for dev).

## Layout

| File | Role |
|------|------|
| `js/api.js` | HTTP calls to `/ask`, `/health` |
| `js/state.js` | In-memory conversation for the API |
| `js/render.js` | DOM for thread, cards, sources |
| `js/main.js` | Form wiring, orchestration |
| `css/tokens.css` | Design tokens |
| `css/layout.css` | Responsive shell |
| `css/components.css` | Cards, chips, composer |

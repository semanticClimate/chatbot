# Climate chat — vanilla web client

**Guidelines (layout + content + where to file issues):** [`docs/web-client-guidelines.md`](../docs/web-client-guidelines.md)

Static HTML/CSS/JS that talks to the FastAPI backend (`POST /ask`). ES modules must be served over HTTP (not `file://`).

## Run locally

From repo root:

```bash
cd web_client
python -m http.server 8081
```

Open http://127.0.0.1:8081 — set **API base URL** to `http://127.0.0.1:8800` (or your deployed URL).

Ensure the API allows this origin (e.g. `CLIMATE_API_CORS_ORIGINS=http://127.0.0.1:8081` or `*` for dev).

## Layout & constraints

**Start here:** [`docs/web-client-guidelines.md`](../docs/web-client-guidelines.md) (index + GitHub Issues link).

Deep dives: [`docs/web-client-layout-contract.md`](../docs/web-client-layout-contract.md) · [`docs/web-client-browser-constraints.md`](../docs/web-client-browser-constraints.md)

| File | Role |
|------|------|
| `js/api.js` | HTTP calls to `/ask`, `/health` |
| `js/state.js` | In-memory conversation for the API |
| `js/render.js` | DOM for thread, cards, sources |
| `js/main.js` | Form wiring, book iframe, orchestration (no TOC — jumps from citations only) |
| `js/lang_prefs.js` | Chat language ids (en/fr/es/pt/hi), localStorage persistence |
| `js/ui_strings.js` | Shell + status + empty-thread copy in all UI languages |
| `js/examples_data.js` | Sample questions per language |
| `css/tokens.css` | Design tokens |
| `css/layout.css` | Responsive shell |
| `css/components.css` | Cards, chips, composer |

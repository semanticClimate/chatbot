# Climate chat — frontend

**Guidelines (layout + content + where to file issues):** [`docs/web-client-guidelines.md`](../docs/web-client-guidelines.md)

Static HTML/CSS/JS that talks to the FastAPI backend (`POST /ask`). ES modules must be served over HTTP (not `file://`).

## Run locally

From repo root:

```bash
cd frontend
python -m http.server 8081
```

Open http://127.0.0.1:8081 — set **API base URL** to `http://127.0.0.1:8800` (or your deployed URL).

Ensure the API allows this origin (e.g. `CLIMATE_API_CORS_ORIGINS=http://127.0.0.1:8081` or `*` for dev).

## Source document (corpus)

The API loads one corpus profile at startup. Switch with environment variable before starting the API:

```bash
export CLIMATE_CORPUS_PROFILE=cabook      # Climate Academy Student Book (default)
export CLIMATE_CORPUS_PROFILE=ipcc_syr    # IPCC AR6 SYR Longer Report
```

Profiles are defined in [`climate_streamlit/config/app.defaults.toml`](../climate_streamlit/config/app.defaults.toml). Check the active profile: `curl -s http://127.0.0.1:8800/corpus`.

## Layout & constraints

**Start here:** [`docs/web-client-guidelines.md`](../docs/web-client-guidelines.md) (index + GitHub Issues link).

Deep dives: [`docs/web-client-layout-contract.md`](../docs/web-client-layout-contract.md) · [`docs/web-client-browser-constraints.md`](../docs/web-client-browser-constraints.md)

| File | Role |
|------|------|
| `js/api.js` | HTTP calls to `/ask`, `/health`, `/corpus` |
| `js/state.js` | In-memory conversation for the API |
| `js/render.js` | DOM for thread, cards, sources |
| `js/main.js` | Form wiring, book iframe, orchestration (no TOC — jumps from citations only) |
| `js/lang_prefs.js` | Chat language ids (en/fr/es/pt/hi), localStorage persistence |
| `js/ui_strings.js` | Shell + status + empty-thread copy in all UI languages |
| `js/examples_data.js` | Sample questions per language |
| `css/tokens.css` | Design tokens |
| `css/layout.css` | Responsive shell |
| `css/components.css` | Cards, chips, composer |

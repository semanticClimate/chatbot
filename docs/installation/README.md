# Installation docs

This folder describes how the Climate Academy Streamlit chatbot fits into a deployment picture and how to install it in different contexts.

| Document | Purpose |
|----------|---------|
| [Server architecture](server-architecture.md) | Runtime topology, dependencies, trust boundaries, and operational concerns |
| [Installation architecture](installation-architecture.md) | Environments, layout, prerequisites, persistence, and upgrade paths |
| [Temporary VPS hosting runbook](temporary-vps-hosting-runbook.md) | Stable public URLs on a cheap VPS (~1 month); Docker Compose or systemd; billing and cancellation notes |
| [macOS quick tunnel runbook](mac-quick-tunnel-runbook.md) | Local API + web + Cloudflare Quick Tunnels for remote browser testing |
| [Windows quick tunnel runbook](windows-quick-tunnel-runbook.md) | Same as macOS runbook on Windows (PowerShell scripts) |
| [Serverless local user install outline](serverless-local-user-install-outline.md) | Planned scripts and procedures for naive Windows/Mac installs (outline only; no scripts yet) |
| [Refactor plan: `app.py`](refactor_app_py_plan.md) | Target architecture, **implementation map**, and how to run/test |

The runnable app lives under `climate_streamlit/`; operational setup mirrors the expectations in `climate_streamlit/README.md`.
# Installation and deployment

Guides for running and hosting the Climate Academy chatbot outside local development.

| Document | Description |
|----------|-------------|
| [fastapi_hosting_options.md](fastapi_hosting_options.md) | Lightweight free hosting options for the **FastAPI** API + separate web client |

Related:

- [climate-academy-assistant-explained.md](../climate-academy-assistant-explained.md) — how the assistant works (colleague-facing)
- [../zoom_daily_summary_local_guide.md](../zoom_daily_summary_local_guide.md) — local Zoom summary tooling (separate workflow)

# Web client — canonical guidelines (layout & content)

This file is the **single entry point** for how we build and change the browser chat (`frontend/`). Read it before UI work; then open the linked contracts for detail.

---

## Canonical documents

| Document | Role |
| --- | --- |
| **[`web-client-layout-contract.md`](web-client-layout-contract.md)** | **Layout:** regions, DOM order, breakpoints (`600px`, `1099px` / `1100px`), scroll ownership, sizing. Any shell/grid change **must** update this file in the same PR. |
| **[`web-client-browser-constraints.md`](web-client-browser-constraints.md)** | **Content & runtime:** vanilla ES modules, no `file://`, security (escaped model text, iframe sandbox), CORS/tunnels, **i18n** (`ui_strings.js` for **en / fr / es / pt / hi**), tokens, a11y, storage keys. |
| **[`installation/mac-quick-tunnel-runbook.md`](installation/mac-quick-tunnel-runbook.md)** | Cloudflare Quick Tunnel workflow for Team A → Team B. |

**Cursor:** edits under `frontend/**` should follow [`.cursor/rules/frontend-browser-constraints.mdc`](../.cursor/rules/frontend-browser-constraints.mdc) (it points here and to the two contracts above).

---

## Team workflow — GitHub

**Bugs and feature requests** for this repo go on GitHub Issues:

**https://github.com/semanticclimate/chatbot/issues**

Use Issues for anything that should be **tracked, assigned, or closed** with a clear outcome (repro steps, expected vs actual, screenshots). Link PRs to issues when you fix them.

For **open-ended design discussion**, prefer GitHub **Discussions** if the org enables it; otherwise an Issue with the `discussion` label (or plain title prefix) is fine.

---

## Quick rules (non-exhaustive)

- **Layout:** obey the layout contract; do not reshuffle HEADER / SETTINGS / WORKBENCH / BOOK without updating the doc.
- **Copy:** no new user-visible English-only literals in chrome code — add keys to **`frontend/js/ui_strings.js`** for all five UI languages.
- **Language / API:** chat language persists and is sent as **`response_language`** on **`POST /ask`**; book HTML in the iframe stays **English**.
- **Commits:** if you change behaviour visible to testers, note it in the PR description and open or update an Issue when appropriate.

# Web client — browser & UI constraints

**Read this before changing anything under [`web_client/`](../web_client/)** (HTML, CSS, or JS modules). Treat it as non-negotiable unless the product owner explicitly changes these rules.

---

## Delivery & runtime

- **HTTP(S) only.** The shell is **`type="module"`** ES modules. Opening `index.html` as **`file://`** will not run. Prefer `python -m http.server` (or any static host).
- **Target browsers.** Current evergreen **Chrome / Firefox / Safari / Edge** with **Fetch API**, **`localStorage`**, **`URL`**, and **CSS Grid + Flex**. Do not rely on unmaintained engines without discussion.
- **No bundler.** The client is intentional **vanilla** HTML/CSS/JS. Do not introduce a compile step unless the whole team agrees.

---

## Related docs (read together)

| Document | Topic |
| --- | --- |
| [`docs/web-client-layout-contract.md`](web-client-layout-contract.md) | Regions, breakpoints, scroll ownership |
| This file | Browser/runtime, safety, i18n, UX invariants |

---

## Security & untrusted content

- **Assistant and user text** rendered in the thread must stay **escaped** (see **`render.js`** — no raw `innerHTML` of model prose except via the escaping helpers already used).
- **Book iframe** uses **`sandbox="allow-scripts allow-same-origin"`** only. Loading arbitrary third-party documents in-frame is off-limits unless the sandbox and threat model are revisited.
- **API base URL** is user-supplied data. Never `eval`/construct scripts from it; only use as a URL base for `fetch`/`iframe.src` patterns already in code.

---

## Network & tunnels

- **CORS.** The FastAPI backend must send **`Access-Control-Allow-Origin`** covering the UI origin (`CLIMATE_API_CORS_ORIGINS`), or **`*`** in dev — especially when UI and API are on **different tunnel hostnames**.
- **Quick tunnel setups** may expose **`tunnel-api-base.txt`** on the **web** origin only; behaviour is documented in [`docs/installation/mac-quick-tunnel-runbook.md`](installation/mac-quick-tunnel-runbook.md). Keep that convention if you rename paths.

---

## Internationalization (mandatory shape)

- **No user-visible English-only literals** added in JS/HTML for strings that ship in the chrome (buttons, hints, placeholders, status line, empty states, accessibility labels tied to visuals). Route them through **[`web_client/js/ui_strings.js`](../web_client/js/ui_strings.js)** with entries for **`en`, `fr`, `es`, `pt`, `hi`**.
- **`applyShellUiStrings(lang)`** must run on load and whenever **chat language** changes so labels, placeholders, **`document.title`**, **`html lang`**, and language-select option captions stay coherent.
- **Chat language selector** persists to **`climate_chat_language`** (`lang_prefs.js`); **`POST /ask`** sends **`response_language`** in sync with it.
- **The student book** served in **`#bookFrame`** stays **English**; do not automate translation of that HTML asset in the client.

---

## Layout & motion

- Do not change **breakpoints** (`600px`, `1099px` / `1100px`) or **scroll ownership** without updating **`docs/web-client-layout-contract.md`** in the same change.
- **`#thread`** owns vertical scroll for messages; prefer not to scroll the entire card for long chats unless the contract is amended.

---

## Design tokens & a11y

- Use spacing/radius from **`tokens.css`** (`--space-*`, `--radius-*`, `--touch-min`) unless there is a design reason and the contract/token file is updated.
- Preserve **`aria-label`**, **`role="status"`** on `#statusLine`, and **screen-reader-only** labels for interactive controls (`sr-only`).
- Respect **`env(safe-area-inset-bottom)`** padding on the shell for notched devices.

---

## Persistence keys (do not rename casually)

| Key | Purpose |
| --- | --- |
| `climate_chat_language` | UI + API response language (`lang_prefs.js`) |
| `climate_web_client_api_base` | Stored API URL (`main.js`) |
| Legacy **`climate_web_client_example_lang`** | Migrated once into chat language |

---

## Checklist before submitting a UI change

- [ ] All new chrome strings appear in **`ui_strings.js`** for **all five** UI languages (or justified exception).
- [ ] Language dropdown still updates options + **`applyShellUiStrings`** + thread empty state (**`refreshView`** path).
- [ ] Wide and narrow breakpoints still match the layout contract smoke expectations.
- [ ] **`file://`** is still not assumed; modules still load without a bundler.

**Overview**
**Purpose:** Frontend-centric architecture summary for the Climate Academy chat UI. Focuses on structure, UI components, data/state flow, event handling, and styling. Backend is shown only as a supporting service.

**Code Entry Points**
**`main.js`**: Orchestrates the UI, wires event handlers, persists settings, resolves API base URL, mounts example questions, and coordinates calls between `api.js`, `state.js`, and `render.js`.
**`help.js` / `ui_modals.js`**: Create and manage help, encyclopedia, and external modals/overlays without touching core chat logic.

**Frontend File Organization**
**HTML shell:** `index.html` — app shell with sidebar, header, chat panel, book iframe, and modal placeholders.
**JS modules:** `js/api.js`, `js/main.js`, `js/state.js`, `js/render.js`, `js/ui_modals.js`, `js/help.js`, `js/examples*.js`, `js/lang_prefs.js`, `js/ui_strings.js`.
**CSS:** tokens (`tokens.css`), layout (`layout.css`), components (`components.css`), modals (`modals.css`), sidebar (`sidebar.css`), help (`help.css`).

**UI Structure & Layout**
**Shell / App layout:** `.app` contains a fixed left `nav.sidebar` (collapsible) and `.app-content` (flex column).
**Header:** Branding + controls (settings, developer tools, help) wired by `main.js` and `help.js`.
**Main grid:** `.main-grid` splits viewport into two columns (chat column and book panel) on desktop; becomes single-column stacked panels on mobile via media queries.
**Chat panel (`.panel-chat`):** Contains `#thread` (message list), `#examplesMount` (sample questions), and `#composer` form (textarea and send button).
**Book panel (`.panel-book`):** `#bookFrame` iframe renders the annotated Climate Academy student book (served by backend `/book/document`).
**Modals / Overlays:** Settings, Developer Tools, External Link modal (`externalModal` + `externalFrame`), Encyclopedia modal (`encyclopediaModal` + `encyclopediaFrame`), Help modal (injected by `help.js`).

**UI Components and Interaction**
**Thread rendering:** `render.js` produces message rows: user bubbles, assistant cards, multi-block assistant answers, citation chips, and operator details.
**Citation chips:** Rendered as `.chip` buttons; clicking triggers a callback passed by `main.js` which finds the source metadata and calls `jumpBookToSource()` to postMessage the book iframe.
**Composer:** Submitting the `#composer` form calls `postAsk()` via `api.js` with current conversation history; while waiting, UI shows an optimistic assistant "Thinking..." bubble.
**Example chips:** `examples.js` mounts localized sample questions; clicking a chip fills the composer input.
**Help modal:** `help.js` fetches `docs/client/help-tool.md`, converts markdown→HTML and injects into the modal body.

**State Management & Data Flow**
**Client state:** Minimal, single source: `state.js` exports `conversation` array and helpers (`getConversation`, `setConversation`, `applyConversationFull`, `clearConversation`). CLI-level code treats server-provided `conversation_full` as the source of truth after each successful `/ask`.
**Flow for a user query:**
User submits question → `main.js` reads `getConversation()` and sends `postAsk(base, q, conversation)`.
`api.js` POSTs to `/ask` and returns JSON containing `conversation_full`.
`main.js` calls `applyConversationFull()` to sync state, then `renderThread()` to update DOM.
`render.js` creates cards, citation chips, and binds chip click handlers that route back to `main.js`.
**Optimistic UI:** `main.js` temporarily renders a local `isThinking` assistant message before the API resolves; server response reconciles the state.

**Event Handling & API Triggers**
**POST /ask** — triggered by composer submit (`postAsk` in `api.js`). Request payload: { question, conversation, top_k?, response_language? }.
**GET /book/document** — used to set `bookFrame.src` (`bookDocumentUrl()`), loaded when API base is configured.
**GET /encyclopedia/entry/:id** — used for encyclopedia modal entries (`encyclopediaEntryUrl()`).
**GET /proxy?url=** — used to load proxied external pages into `externalFrame`.
**Health / Ready / Logs / Export** — `getHealth`, `getReady`, `fetchLogsCsvBlob`, `exportConversationCsv` provide diagnostics and export actions available from sidebar and modals.
**Iframe postMessage bridge:** The book iframe and host page communicate via `window.postMessage`:
From book → host: `ca-encyclopedia-open` (open encyclopedia modal), `ca-external-link-open` (open external modal), `ca-encyclopedia-preview` (term preview tooltip with coordinates).
From host → book: `ca-jump` / `ca-jump-para` messages to scroll/highlight book to a citation.

**Rendering Responses**
Server returns structured messages: assistant blocks, citations, and sources. `render.js`:
Renders blocks into `.card` elements.
Renders `.chips` for citations within a block using `sources` metadata.
Binds chip clicks to `onPickSource` which `main.js` supplies to call `jumpBookToSource()`.
Operator details (diagnostics) rendered inside `<details>`.

**Routing / Navigation**
No client-side URL routing (no SPA router). Navigation is iframe-based and modal-driven: the book and encyclopedia content live in iframes; modals are shown/hidden by toggling `.help-visible` classes.
Sidebar collapse/expand toggles are purely DOM class toggles (no route changes).

**Styling Architecture**
**Design tokens:** `tokens.css` provides color, spacing, radii, fonts and semantic variables.
**Layered CSS:** `layout.css` controls grid, shell, responsive breakpoints; `components.css` defines components (buttons, cards, chips, frames); `modals.css` and `sidebar.css` contain focused overrides and theme tweaks.
**Responsive:** Desktop uses 2-column grid (`grid-template-columns: 57% 41%`); mobile switches to stacked flow and repurposes expanded/collapsed classes.
**Modals:** Implemented as overlaid elements with `.help-overlay` and `.help-modal` classes; `ui_modals.js` handles open/close, focus, Escape key, and overlay clicks.

**How Frontend Talks to Backend (concise)**
Primary interaction is via `api.js` to the FastAPI server. Important endpoints:
POST `/ask` — main Q&A with RAG/LLM; returns the full conversation and metadata (blocks, sources).
GET `/book/document` — annotated student book HTML (iframe content).
GET `/encyclopedia/entry/:id` — encyclopedia iframe content.
GET `/proxy?url=` — proxied external pages for the external modal.
Diagnostics: `/health`, `/ready`, `/logs/export`, `/conversation/export`.
Frontend keeps API base URL in `#apiBaseUrl` (persisted in localStorage) and builds endpoint URLs via `api.js` helpers.

**Key Implementation Notes / Observations**
The app intentionally keeps client state minimal; it relies on server-provided `conversation_full` to avoid duplication of conversation logic.
Iframe-based book + postMessage bridge keeps the book isolated while enabling precise navigation and previews.
Styling uses CSS custom properties centrally (`tokens.css`) for easy theming.
No heavy framework — pure ES modules + DOM APIs, intentionally small and readable.

**Files to inspect for details**
[index.html](index.html)
[js/main.js](js/main.js)
[js/api.js](js/api.js)
[js/state.js](js/state.js)
[js/render.js](js/render.js)
[js/ui_modals.js](js/ui_modals.js)
[css/tokens.css](css/tokens.css)
[css/layout.css](css/layout.css)
[css/components.css](css/components.css)
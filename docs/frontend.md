## Technical Guide to the Frontend Architecture

### Purpose

This document explains the frontend side of the refactored climate chatbot codebase. It is written as a practical guide for a new intern or contributor who needs to understand what each main frontend module does and how the UI is assembled.

The frontend is the browser-facing part of the application. It is responsible for:
- page layout
- chat interactions
- sidebar behavior
- language selection
- modal windows
- API calls to the backend
- rendering messages and sources
- book and encyclopedia viewer actions
- client-side state

The main frontend entry point is:

- `frontend/index.html`
- `frontend/js/app.js`

---

## 1. Frontend overview

The frontend is organized under `frontend/` and split into:
- `index.html` — the main HTML shell
- `css/` — layout, components, sidebar, modal, token, and help styling
- `js/` — modular JavaScript grouped by responsibility
- `assets/` — images and media used by the UI
- `docs/` — frontend-specific documentation

The old frontend was more tightly bundled. The refactored frontend is designed as a modular client application.

---

## 2. Page shell: `frontend/index.html`

This file defines the structure of the browser UI.

### What it contains

The page includes:
- a left sidebar for tools and actions
- the main chat workspace
- a book panel
- an encyclopedia modal/viewer
- external-link modal
- health modal
- settings modal
- help modal
- overlays for modal dismissal
- shared UI labels and controls

### Important IDs to know

Some of the most important element IDs are:
- `sidebar`
- `btnSidebarToggle`
- `btnClear`
- `btnExportChat`
- `btnExportLogs`
- `btnHealth`
- `chatLangSelect`
- `question`
- `thread`
- `bookFrame`
- `encyclopediaFrame`
- `externalFrame`
- `settingsModal`
- `help`-related controls and overlays

These IDs are used heavily by the JavaScript modules.

### Why this matters

If the DOM structure changes, the frontend modules that call `document.getElementById(...)` will need to be updated too.

---

## 3. Bootstrap file: `frontend/js/app.js`

This is the frontend entry point.

### Main function

#### `wire()`
This is the main bootstrapping function. It runs after the DOM is ready and connects the different frontend modules.

It typically:
- applies UI strings
- loads the chat language
- resolves the API base URL
- mounts example questions
- updates status text
- wires the book panel
- sets up tooltips
- initializes sidebar behavior
- wires chat actions and language controls

### Why this file is intentionally small

`app.js` should stay small. Its job is to initialize the application, not to implement every behavior directly. This is a good modular design choice because it keeps the startup path understandable.

---

## 4. Core helpers

### `frontend/js/core/dom.js`

This module stores reusable DOM and URL helpers.

#### Main functions

##### `$ (id)`
Returns the element with the given ID or throws a clear error if the element is missing.

##### `trimBaseUrl(baseUrl)`
Removes trailing slashes from a URL or base path.

##### `apiOriginFromBase(baseUrl)`
Converts a base URL into a clean origin string for display or comparison.

##### `triggerBrowserDownload(...)`
Used by export flows to trigger a file download in the browser.

### Why it matters

These small helpers reduce duplication across the UI modules.

---

### `frontend/js/core/api_base.js`

This module isolates backend-origin detection and saved API base behavior.

#### Main functions

##### `isRemoteWebOrigin()`
Checks whether the page is being served from a tunnel/public hostname rather than localhost.

##### `isLoopbackApiBase(base)`
Checks whether a base URL is local.

##### `isAcceptableApiBase(base)`
Validates whether a base URL is usable.

##### `fallbackApiBase()`
Returns the best fallback API base when no saved value exists.

##### `loadApiBase()`
Loads the saved API base from storage or the environment-aware default.

##### `resolveInitialApiBase()`
Chooses the initial backend base URL used by the app.

##### `saveApiBase(base)`
Stores the selected API base so it can be reused.

### Why this matters

This module is the answer to “where is the backend?” That logic should not be mixed into the chat UI or rendering code.

---

## 5. API layer on the frontend

### `frontend/js/api/api.js`

This module owns the HTTP layer and has no UI dependencies.

#### Main functions

##### `postAsk(baseUrl, question, conversation, opts={})`
Sends the main question request to the backend `/ask` endpoint.

##### `getHealth(baseUrl)`
Calls the backend `/health` endpoint.

##### `getReady(baseUrl)`
Calls the backend `/ready` endpoint.

##### `bookDocumentUrl(baseUrl)`
Builds the backend URL for the book document.

##### `encyclopediaEmptyUrl(baseUrl)`
Builds the backend URL for the encyclopedia placeholder.

##### `encyclopediaEntryUrl(baseUrl, entryId)`
Builds the backend URL for a specific encyclopedia entry.

##### `exportConversationCsv(baseUrl, conversation)`
Sends a conversation export request.

##### `fetchLogsCsvBlob(baseUrl)`
Fetches the backend logs CSV as a downloadable blob.

### Why this is useful

This module centralizes all fetch logic so the rest of the UI does not need to know how endpoint URLs are built.

---

### `frontend/js/api/chat.js`

This module groups the chat-specific UI workflows.

#### Main functions

##### `fitSelectToLongestOption(...)`
Adjusts the language select width so labels fit properly.

##### `wireChatLanguageSelect(...)`
Connects the language dropdown to the UI state.

##### `scrollThreadToBottom(...)`
Keeps the chat thread scrolled to the newest message.

##### `refreshView(...)`
Refreshes the chat display from the current state.

##### `clearChat(...)`
Clears the current conversation state and refreshes the interface.

##### `handleHealthCheck(...)`
Triggers a health check request and displays the result.

##### `handleExportChat(...)`
Exports the current conversation.

##### `handleExportLogs(...)`
Downloads the logs CSV.

##### `handleSubmitQuestion(...)`
Handles the main send-message flow.

##### `wireLanguageChange(...)`
Updates language-driven UI strings and behavior.

### Why this module exists

Chat behavior is a workflow, not just a button click. Keeping it in a separate file makes the main app bootstrap much cleaner.

---

## 6. Shared UI state

### `frontend/js/state/state.js`

This module stores client-side conversation state.

#### Main functions

##### `getConversation()`
Returns the current conversation state.

##### `setConversation(next)`
Replaces the current conversation state.

##### `clearConversation()`
Resets the conversation to an empty state.

##### `applyConversationFull(full)`
Replaces the local state with the full conversation payload returned by the backend.

### Why this matters

The client needs a single source of truth for conversation content. This module provides that source of truth.

---

## 7. UI rendering

### `frontend/js/ui/render.js`

This module renders the visible chat and source UI.

#### Main functions

##### `renderSourceDetail(el, source)`
Renders a source metadata panel into the supplied element.

##### `renderThread(el, conversation)`
Renders the full conversation thread.

##### `setStatus(el, message, kind)`
Updates status text and styling.

### Why this file is important

This is one of the safest places to modify UI behavior because it keeps rendering separate from API calls and state management.

---

### `frontend/js/ui/ui_strings.js`

This module stores the client UI strings for multiple languages.

#### Main functions

##### `setUiLanguage(code)`
Sets the UI language used for shell text.

##### `getUiLanguage()`
Returns the current UI language.

##### `t(key, vars)`
Returns the localized string for a given key.

##### `htmlLangFor(lang)`
Maps chat language codes to HTML `lang` values.

##### `applyShellUiStrings()`
Updates shell text and language-dependent labels in the UI.

### Why this matters

This module keeps user-facing copy out of the chat logic.

---

### `frontend/js/ui/ui_modals.js`

This module handles open/close behavior for shell modals.

#### Main function

##### `bindAppModal(triggerId, overlayId, dialogId)`
Attaches modal open/close handlers to the specified modal elements.

### Why this file exists

Modal behavior is repetitive, so it is kept in one small reusable helper rather than duplicated across the UI.

---

### `frontend/js/help.js`

This is the standalone help module.

#### Main functions

##### `markdownToHtml(md)`
Converts a limited subset of Markdown into HTML.

##### `closeList(...)`
Internal helper for list rendering.

##### `openHelp()`
Opens or initializes the help modal.

##### `initHelp()`
Sets up the help module.

### Why it is separate

The help module is intentionally isolated so that the rest of the application still works even if help fails to initialize.

---

### `frontend/js/ui/lang_prefs.js`

This module handles language preference logic.

#### Main functions
- `normalizeChatLangId(...)`
- `loadChatLanguage()`
- `saveChatLanguage(...)`

It helps keep the selected chat language stable across sessions.

---

## 8. Frontend features

### `frontend/js/features/sidebar.js`

#### Main function

##### `initSidebarToggle()`
Handles expanding and collapsing the sidebar, plus overlay clicks.

### Why this matters

Sidebar behavior is independent from chat behavior, so keeping it in a dedicated module is clean and easy to maintain.

---

### `frontend/js/features/tooltip.js`

#### Main function

##### `showTermPreviewTooltip(text, x, y, visible)`
Shows or hides the floating preview tooltip for terms in the book view.

### Why this matters

This module is deliberately tiny, but separating it keeps tooltip behavior easy to evolve.

---

### `frontend/js/features/book.js`

This is one of the most important frontend modules because it connects the book iframe, encyclopedia iframe, and external-link modal.

#### Main functions

##### `jumpBookToSource(source, targetOrigin)`
Tells the embedded book iframe to jump to the source location associated with a retrieved chunk.

##### `syncBookPanel(...)`
Synchronizes the book panel with the active source.

##### `syncEncyclopediaPanel(...)`
Synchronizes the encyclopedia panel when an entry is selected.

##### `openEncyclopediaEntry(...)`
Opens an encyclopedia entry in the embedded viewer.

##### `openExternalLinkModal(...)`
Opens the external-link modal.

##### `showTermPreviewTooltip(...)`
Exports the tooltip function from this feature area as part of the book interaction set.

### Why this module matters

This module is the bridge between retrieval results and what the user sees in the book/encyclopedia pane.

---

### `frontend/js/features/chat.js`

This module contains the chat-workflow behavior from the browser side.

#### Main functions
- language wiring
- view refresh
- clearing the chat
- health check
- export chat
- export logs
- submit question
- updating the book source after new results

### Why this module matters

It is the front-end counterpart of the backend chat orchestration path.

---

## 9. Example content and support data

### `frontend/js/examples/examples.js`

#### Main functions
- `fillChipsForLang(...)`
- `mountExampleQuestions(...)`
- `refill(...)`

This module populates sample questions based on the current language.

### `frontend/js/data/examples_data.js`

This file stores example question data used by the examples module.

### Why this matters

Example questions help new users understand what the chatbot can do without forcing them to type from scratch.

---

## 10. The frontend CSS architecture

The frontend styling is split into dedicated stylesheets:

- `css/tokens.css` — design tokens and base values
- `css/layout.css` — page layout and structure
- `css/components.css` — reusable UI components
- `css/modals.css` — modal overlays and dialogs
- `css/sidebar.css` — sidebar-specific styling
- `css/help.css` — help module styling

### Why this split helps

Styling changes are easier to manage when layout, components, and modal logic are not all mixed in one stylesheet.

---

## 11. Frontend runtime flow

A simplified flow for the browser UI is:

1. `index.html` loads the page shell and CSS.
2. `app.js` bootstraps the app after the DOM is ready.
3. `api_base.js` resolves the backend origin.
4. `ui_strings.js` loads the language-dependent shell text.
5. `chat.js` wires the chat workspace.
6. `book.js` and `tooltip.js` wire the viewer interactions.
7. `render.js` draws the conversation and source details.
8. `api.js` sends requests to the backend.
9. `state.js` stores conversation state locally.

That is the main client-side architecture.

---

## 12. What a new contributor should learn first

If you are new to the frontend, start in this order:

1. `frontend/index.html`
2. `frontend/js/app.js`
3. `frontend/js/core/api_base.js`
4. `frontend/js/api/api.js`
5. `frontend/js/api/chat.js`
6. `frontend/js/state/state.js`
7. `frontend/js/ui/render.js`
8. `frontend/js/features/book.js`
9. `frontend/js/features/chat.js`
10. `frontend/js/ui/ui_strings.js`

That gives a practical overview of how the UI boots, talks to the backend, and updates the page.

---

## 13. Frontend summary

The frontend has been refactored into a more maintainable client structure.

The key design ideas are:
- `index.html` defines the page shell
- `app.js` bootstraps the client
- `core/` handles shared helpers
- `api/` owns fetch logic
- `features/` owns behavior around sidebar/chat/book/tooltip
- `state/` owns client state
- `ui/` owns rendering and UI strings
- `help.js` is isolated as a safe standalone tool
- `css/` is split by concern

This makes the frontend much easier for a new intern to understand and extend without getting lost in one giant script.

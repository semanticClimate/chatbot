# Climate Academy Web Client — UX Improvements Log

> **Session date:** 2026-06-07  
> **Scope:** Encyclopedia modal, tooltip system, term-preview tooltips, direct-open UX fix, hierarchical Back navigation.

---

## 1. Encyclopedia → Modal Overlay (was: inline panel)

### Problem
The Encyclopedia was rendered as a second iframe *beneath* the Student Book inside `panel-book`. This caused:
- Layout cramping — the book and encyclopedia competed for height.
- Navigation confusion — clicking a term scrolled the page, and returning to the chat required manual scrolling back up.
- The `scrollIntoView` call was unreliable when overflow was hidden at the grid level.

### Solution
Moved the Encyclopedia to a **`help-modal` overlay** (`#encyclopediaModal` / `#encyclopediaOverlay`), following the exact same pattern already used for Settings, Developer Tools, and the Wikipedia/Wikidata viewer.

**Files changed:**
| File | Change |
|---|---|
| `web_client/index.html` | Removed inline `encyclopedia-toolbar` + `encyclopediaFrame` from `panel-book`. Added `#encyclopediaModal` overlay block. |
| `web_client/js/main.js` | `openEncyclopediaEntry()` now opens the modal overlay instead of calling `scrollIntoView`. `syncEncyclopediaPanel(base, null)` clears the iframe src on reset. |
| `web_client/js/ui_modals.js` | Added `initEncyclopediaModal()` — wires ✕ button, overlay-click, ESC key, and the new Back button. |
| `web_client/css/components.css` | Added `.encyclopedia-modal`, `.encyclopedia-modal-header`, `.encyclopedia-modal-body`, `.encyclopedia-frame-modal`. Removed dead `.encyclopedia-toolbar` / `.encyclopedia-frame` rules. `book-frame` changed from `flex: 5` to `flex: 1` to fill the full panel. |
| `web_client/css/layout.css` | `panel-book` changed from `height: 88vh; overflow-y: auto` to `height: 100%; overflow: hidden` — uses full column now that encyclopedia is a modal. |

**Removed import:** `encyclopediaEmptyUrl` was removed from `main.js` imports — no longer needed since the modal simply clears its src rather than loading a placeholder page.

---

## 2. Tooltip System

### Problem
All icon-only and action buttons had no accessible description. Users hovering over the gear ⚙️ or wrench 🔧 icons had no way to know their purpose.

### Solution
Implemented a **zero-dependency CSS+JS tooltip system**:

- Added `data-tooltip="…"` attributes to every major button in `index.html`.
- A single `#appTooltip` `<div>` is positioned via JS (`fixed`, `z-index: 9999`, `pointer-events: none`).
- `initButtonTooltips()` in `ui_modals.js` wires `mouseenter`/`mouseleave` (and `focus`/`blur`) for all `[data-tooltip]` elements.
- Positioning logic: centers below the target, clamps to viewport edges, flips above if it would overflow the bottom.

**Tooltips added:**

| Button | Tooltip |
|---|---|
| Clear chat | "Clear all chat messages and reset the conversation." |
| Download chat | "Download exported conversation data as CSV." |
| Server logs | "Download server logs as CSV." |
| Settings ⚙️ | "Open language and display settings." |
| Developer Tools 🔧 | "Open developer tools and advanced settings." |
| Send | "Send message." |
| Reset highlight | "Reset all highlights and return the book to the top." |
| Encyclopedia Back | "Return to the Student Book and chatbot." |

**Files changed:** `index.html` (data-tooltip attrs), `web_client/css/components.css` (`.app-tooltip`, `.app-tooltip-visible`), `web_client/js/ui_modals.js` (`initButtonTooltips()`).

---

## 3. Term-Preview Tooltip Infrastructure

### Goal
When a user hovers over a highlighted encyclopedia term in the Student Book, show a lightweight preview of the encyclopedia entry (e.g. first sentence) without opening the full modal.

### Implementation
The host shell listens for `ca-encyclopedia-preview` postMessages from the book iframe:

```js
// In main.js — postMessage handler
if (ev.data?.type === "ca-encyclopedia-preview") {
  showTermPreviewTooltip(
    ev.data.text || "",
    ev.data.x ?? 0,
    ev.data.y ?? 0,
    ev.data.visible ?? false
  );
}
```

`showTermPreviewTooltip()` translates iframe-relative coordinates to viewport coordinates using `bookFrame.getBoundingClientRect()`, then positions the `#appTooltip` element accordingly with overflow-edge auto-flip.

### ⚠️ Pending — Book iframe side
The book iframe (`book_encyclopedia_links.js`) does **not yet emit** `ca-encyclopedia-preview` messages. This requires the backend to:
1. Load a preview snippet (first sentence / summary) for each term — either embedded as a `data-preview` attribute on the `<a>` tags at render time, or fetched on hover via a lightweight API call.
2. Add `mouseover`/`mouseout` listeners that `postMessage` to the parent with `{ type: "ca-encyclopedia-preview", text, x, y, visible }`.

This is intentionally left as a separate task since it requires a backend data change.

---

## 4. Direct-Open UX Fix (Green Flash on Click)

### Problem
When clicking a highlighted encyclopedia term, a **green background flash** appeared briefly before the modal opened. This was particularly noticeable on slower machines or when the modal animation was running.

### Root cause
`cabook_links.css` defined a `:hover` background of `#e8f4ee` (green) on `.ca-encyclopedia-link`. During the `mousedown`→`mouseup` cycle, the browser keeps the hover paint active while:
1. The click event fires.
2. `e.preventDefault()` is called.
3. The postMessage round-trip completes.
4. The modal CSS transition animates in (250ms).

The green background persisted for the entire 250–400ms window, creating a visible flash.

### Fix
Added `:active` rules to `encyclopedia/assets/cabook_links.css` that explicitly clear the background on click:

```css
a.ca-encyclopedia-link:active {
  background: transparent;
  color: #0d3d26;
  opacity: 0.7;
  transition: opacity 0.05s ease;
}
```

The same pattern was applied to `ca-wikipedia-link` and `ca-wikidata-link` for consistency.

**File changed:** `encyclopedia/assets/cabook_links.css`

> **Note:** This CSS is injected into the **book iframe** and **encyclopedia entry pages** at render time by `build_annotated_book_document()` and `build_encyclopedia_entry_document()` respectively (via `link_css_path()`). Changes take effect on the next book/entry load — a browser hard-refresh may be needed if the server caches the document.

---

## 5. Hierarchical Back Navigation

### Goal
Create a consistent, intentional navigation stack:

```
Chatbot → Encyclopedia → Wikipedia/Wikidata
Wikipedia/Wikidata ← Back → Encyclopedia
Encyclopedia       ← Back → Chatbot
```

### Problem with naive implementation
Both the Encyclopedia modal and the Wikipedia/Wikidata modal use the same `z-index: 901`. Showing both simultaneously would cause visual stacking/overlap with no clean order guarantee (dependent on DOM order, which is fragile).

### Solution — Hide-not-Destroy + data-attribute bridge

When `openExternalLinkModal()` is called while the encyclopedia is open:

1. The encyclopedia modal is **hidden** (`help-visible` removed) but its `<iframe src>` is **preserved** (not cleared).
2. A `data-from-encyclopedia="1"` attribute is stamped on `#externalModal` to record the navigation context.

When the external modal's Back button is clicked (`initExternalModal()`):

1. The external modal closes normally (iframe src cleared).
2. If `data-from-encyclopedia === "1"`: the encyclopedia overlay + dialog have `help-visible` re-added. Because the iframe src was preserved, the encyclopedia content **restores instantly** with no network request.

When the encyclopedia modal's Back button is clicked (`initEncyclopediaModal()`):

1. The encyclopedia closes completely (iframe src cleared).
2. The user returns to the chatbot/Student Book view.

**Cross-module state:** The `data-from-encyclopedia` attribute lives on the DOM element itself, making it readable by both `main.js` (which sets it) and `ui_modals.js` (which reads it) without any ES module import/export dependency.

### Hiccup: module isolation
Initially `notifyExternalModalOpening()` was written as a function in `ui_modals.js` intended to be called from `main.js`. However, both scripts are `type="module"`, meaning module-scope functions are **not** accessible on `window` and not importable without explicit `export`. Rather than adding an export chain, we moved the state to a DOM data attribute which both scripts can freely read/write — a simpler and more robust solution.

**Files changed:** `web_client/js/main.js` (`openExternalLinkModal`), `web_client/js/ui_modals.js` (`initExternalModal`, `initEncyclopediaModal`), `web_client/index.html` (Back button added to encyclopedia modal header).

---

## Known Hiccups & Decisions

| Issue | Resolution |
|---|---|
| **Scroll-removal broke navigation** | The original fix for "blank space below" used `overflow: hidden` everywhere, which made the encyclopedia panel unreachable after opening. Solved by converting encyclopedia to a modal. |
| **`encyclopediaEmptyUrl` unused import** | After moving to modal, the placeholder URL was no longer needed. Import removed to keep the module clean. |
| **`88vh` book panel height** | The `panel-book` was set to `height: 88vh` to share space with the encyclopedia. Now changed to `height: 100%` filling the full column. |
| **`flex: 5 / 1.5` ratio** | The book and encyclopedia iframes used a flex ratio split. After removing the encyclopedia from the panel, `book-frame` changed to `flex: 1; min-height: 0`. |
| **Term-preview requires backend work** | The preview tooltip infrastructure is wired on the host side but the book iframe doesn't yet emit preview events. Requires a backend `data-preview` attribute or hover API. |
| **Green flash root cause** | Was mistaken for an overlay element initially. Root cause was `:hover` background persisting through the modal animation window. Fixed with `:active { background: transparent }`. |
| **Module cross-talk** | Tried function call across modules; resolved with DOM data-attribute to avoid ES module export chain complexity. |

---

## File Reference

```
web_client/
  index.html                           ← Modal HTML, data-tooltip attrs, #appTooltip
  js/
    main.js                            ← openEncyclopediaEntry(), openExternalLinkModal(),
                                         showTermPreviewTooltip(), syncEncyclopediaPanel()
    ui_modals.js                       ← initEncyclopediaModal(), initExternalModal(),
                                         initButtonTooltips()
  css/
    components.css                     ← .encyclopedia-modal-*, .app-tooltip, .book-frame
    layout.css                         ← .panel-book (height:100%)

encyclopedia/assets/
  cabook_links.css                     ← :active rules for green-flash fix
```

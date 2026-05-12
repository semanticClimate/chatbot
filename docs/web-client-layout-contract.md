# Web client shell — layout contract

**Canonical index:** [`docs/web-client-guidelines.md`](web-client-guidelines.md) (layout + browser rules + GitHub Issues). This file is the **layout** slice only.

This document freezes the **structural layout** of the Climate Academy chat (`web_client/`): named regions, breakpoints, scroll ownership, and min/max sizing. **Do not ship visual tweaks that reshuffle regions or alter these breakpoints unless this file is updated in the same change.**

Implementation lives primarily in [`web_client/css/layout.css`](../web_client/css/layout.css), with book and composer details in [`web_client/css/components.css`](../web_client/css/components.css) and spacing/radii in [`web_client/css/tokens.css`](../web_client/css/tokens.css). Markup: [`web_client/index.html`](../web_client/index.html).

---

## 1. Landmark regions (DOM order)

| Contract name | Element | Classes / notes | Landmark |
| --- | --- | --- | --- |
| **HEADER** | `<header>` | `app-header`: title + subtitle | implicit header |
| **SETTINGS** | `<section>` | `panel panel-settings`; chat language `#chatLangSelect`, API URL, actions, CSV `<details>` | `aria-label="Connection"` |
| **WORKBENCH** | `<div>` | `main-middle` — not a landmark; grouping wrapper | — |
| **CHAT** | `<section>` | `panel panel-chat`; `#thread`, `#examplesMount`, `#composer` | `aria-label="Conversation"` |
| **SOURCES** | `<aside>` | `panel panel-sources` `#sourcesPanel` | `aria-label="Sources"` |
| **BOOK** | `<section>` | `panel panel-book`; toolbar + `#bookFrame` | `aria-label="Student book"` |

**`main`** uses class `main-grid` and wraps **WORKBENCH** + **BOOK** only. HEADER and SETTINGS sit **outside** `<main>` to keep reading order stable.

---

## 2. Intended layout (conceptual grid)

Treat the viewport as stacking **HEADER → SETTINGS → MAIN**. **MAIN** behaves as follows.

### Narrow: viewport width `< 1100px`

Logical column — single stack:

```
MAIN (1 column):
  WORKBENCH
    CHAT (flex column)
    SOURCES (directly below CHAT)
  BOOK (below WORKBENCH)
```

### Wide: viewport width ≥ `1100px`

Logical two-column **main grid** (`main-grid`):

| Column | Tracks (CSS) | Content |
| --- | --- | --- |
| **Left** | `minmax(280px, 1fr)` | Entire WORKBENCH (CHAT atop SOURCES) |
| **Right** | `minmax(320px, 1.15fr)` | BOOK |

Suggested **frozen** mental model (`grid-template-areas` wording only — naming for this contract, not necessarily present in CSS today):

Wide:

```text
grid-template-columns: minmax(280px, 1fr) minmax(320px, 1.15fr);
/* left cell = WORKBENCH, right cell = BOOK */
```

Narrow falls back to a single implicit row stack with the **same subtree order**.

**Rule:** Do not reorder CHAT vs SOURCES inside WORKBENCH, and do not place BOOK **between** them without revising this contract (and UX).

---

## 3. Breakpoints (frozen)

| Name | Condition | Behaviour |
| --- | --- | --- |
| **COMPOSER** | `max-width` **599px** (`< 600px`) | Composer: column (textarea stacked above Send). |
| **COMPOSER** | `min-width: 600px` | Composer: row (Send aligned to bottom). |
| **MAIN** | `< 1100px` | `main-grid`: one column; column gap `var(--space-md)`. |
| **MAIN** | `≥ 1100px` | `main-grid`: two columns as in §2; `align-items: stretch`. |
| **SOURCES sticky** | `max-width: 1099px` | SOURCES: `position: sticky; bottom: 0; z-index: 2; max-height: 40dvh; overflow-y: auto`. |
| *(wide)* | `≥ 1100px` | Sticky_SOURCES rules **do not apply** (`panel-chat` max-height unrestricted vs narrow cap). |

**Note:** Sticky_SOURCES uses **`1099px`** and MAIN-wide uses **`1100px`** — a deliberate 1px handoff so behavior does not overlap.

Changing any of these thresholds requires updating this table and validating CHAT/SOURCES/BOOK interplay on real devices.

---

## 4. Scroll ownership

| Region | Scrolls? | Mechanism |
| --- | --- | --- |
| **page/body** | Default document scroll | Allowed; safe-area respected on `.app` bottom padding. |
| **THREAD** (`#thread`) | **Yes** | `flex: 1; overflow-y: auto` inside CHAT (`-webkit-overflow-scrolling: touch`). |
| **CHAT shell** (`panel-chat`) | No (except thread) | Column flex; `min-height/min(48dvh,480px)`, `max-height: 78dvh` (narrow sizing intent). Wide: `max-height: none`. |
| **SOURCES** (`#sourcesDetail` area) | **When narrow + panel overflows** | Panel gets `overflow-y: auto` with `max-height: 40dvh` via sticky_SOURCES. |
| **BOOK iframe** | Internal | Iframe owns its document scroll; host gives fixed `height`/`min-height` on `.book-frame`. |

**Rule:** Prefer **THREAD** absorbing conversation growth; avoid making the entire **CHAT** panel the only scroll unless this contract changes.

---

## 5. Sizing constraints (frozen intent)

| Element | Constraints |
| --- | --- |
| **Shell `.app`** | `max-width: min(1680px, 100%);` horizontal centering; padding `var(--space-md)`, bottom respects `safe-area-inset-bottom`. |
| **`panel-chat`** | `min-height: min(48dvh, 480px)`, `max-height: 78dvh` below wide MAIN; wide MAIN removes chat `max-height` cap via media rule. |
| **`panel-sources`** (narrow) | Sticky footer band: `max-height: 40dvh`. |
| **`.book-frame`** | `min-height: 360px`; `height: min(62dvh, 680px)`; width 100%. |
| **User bubbles** (content) | `max-width: min(92%, 560px)` (components layer). |

---

## 6. Design tokens touching layout (subset)

Canonical definitions: [`tokens.css`](../web_client/css/tokens.css).

| Token | Typical use in shell |
| --- | --- |
| `--space-xs` … `--space-lg` | Gaps, padding between regions |
| `--touch-min` | Minimum tap targets (`44px`), inputs/buttons |
| `--radius-*` | Panel and control corners |
| `--shadow-soft` | Panel elevation |

New layout spacing should prefer **these tokens**, not arbitrary `px`, unless this contract introduces a documented exception.

---

## 7. Change control

1. Update **§2–§5** when DOM order, breakpoints, scroll model, or min/max envelopes change.
2. Update **`*.mmd` / screenshots** under [`docs/architecture/`](architecture/) only if diagrams are maintained for the shell (optional).
3. After CSS edits, smoke-test **both sides** of `1100px` and `600px`, and SOURCE stickiness near `1099px`.

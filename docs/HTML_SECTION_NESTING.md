# Climate Academy book HTML — nesting and numbering (2026-03-19, system date of generation)

## Survey and recommended scheme

The PDF pipeline flattens structure; HTML lets us preserve **nested outline** and stable **decimal section numbers** (1, 1.1, 1.1.2) for citations in RAG answers.

### Root container

- Wrap the book in **one** root element, preferably:
  - `<article id="climate-academy-book" lang="en">`  
  The parser resolves root in this order: `article#climate-academy-book` → `article.book` → `main` → `body`.

### Outline nodes

- Use **nested `<section>`** elements as outline nodes (one node per outline unit you want numbered).
- Put the **human title** in a heading (`<h1>`–`<h6>`) in the **intro** of that section (before nested `<section>` children), so the title is not mistaken for a subsection title.

### Explicit depth (`data-outline-level`)

- On each `<section>`, set **`data-outline-level="1"`** through **`6"`** for the intended depth in the decimal outline.
- This is **more reliable than heading tags alone** (e.g. you may style with `<h2>` but want outline level 1).
- If `data-outline-level` is omitted, the parser uses the **first applicable heading** under direct (non–nested-section) content, else defaults to `parent_depth + 1`.

### Decimal numbering rules (automatic)

- Numbering is **depth-first** in document order.
- On entering a section at outline depth \(d\) (1-based), the engine:
  1. Increments counter at depth \(d\).
  2. Resets counters at depths \(d+1 \ldots 6\) to zero.
- Displayed id is `counters[0].counters[1]...counters[d-1]` joined with dots (e.g. `1.2.3`).

### Body text for RAG

- **Intro material** for a section = all **direct** child nodes that are **not** `<section>` (paragraphs, lists, figures, headings, etc.).
- **Nested `<section>`** elements become child outline nodes; their text is **not** duplicated in the parent’s body (avoids double indexing).

### Optional front matter

- A `<header>` with the book title is fine; it is not required to be a numbered `<section>`.

### Prototype file

- See `<root>/input/sample_ca_book.html` for the minimal subset example.

## Visible section numbers in the viewer (2026-05-18)

RAG citations and “View source” jumps use decimal section ids (`1`, `1.2`, `1.2.3`). Those ids must also appear **in the book iframe** so readers can match a chat citation to the heading they see.

### Pipeline

1. **`annotate_html_with_section_ids()`** (`climate_streamlit/html_sectioning.py`) assigns `data-section-number` on outline nodes and stamps the same value on each section’s title heading.
   - **Format A** (nested `<section data-outline-level="…">`): number on `<section>` and on the first title `<h1>`–`<h6>` in that section.
   - **Format B** (flat export, `<h1>`–`<h3>` only): number on the heading and on a wrapping `<div class="ca-section">` around heading + body.
2. **`inject_book_viewer_assets()`** (`climate_streamlit/rag/book_document.py`) injects `climate_streamlit/assets/book_iframe_highlight.css` and `book_iframe_jump.js` into the HTML served to Streamlit, FastAPI (`/book/document`), and the static web client iframe.

### Display rule (CSS)

Headings that carry `data-section-number` render a prefix via `::before`:

```css
:is(h1, h2, h3, h4, h5, h6)[data-section-number]::before {
    content: "§ " attr(data-section-number) " — ";
}
```

Example visible title: **§ 1.2 — The greenhouse effect** (same shape as RAG prompt headers `[§ 1.2 — …]`).

### What stays unnumbered

- Skippable front-matter `<h1>` ids (`section`, `contents`, …) and headings with no body text (same rules as the parser).
- The book title in `<header>` when it is not a numbered `<section>`.

### Tests

- `tests/test_html_sectioning.py` — heading stamps (formats A and B), CSS injection, asset file contains the visible-§ rule.

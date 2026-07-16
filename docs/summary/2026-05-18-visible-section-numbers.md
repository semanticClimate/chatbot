# Session summary — visible § section numbers in CA book HTML

Date: **2026-05-18** (workspace context).

## Problem

The Climate Academy student book HTML showed section titles without decimal outline numbers. RAG answers and “View source” already cited sections as `§ 1.2 — Title`, but the iframe viewer only stored numbers in `data-section-number` attributes — nothing rendered them for readers.

## Solution (two parts)

### 1. Stamp numbers on headings (annotation)

`annotate_html_with_section_ids()` in `backend.app/html_sectioning.py` already assigned `data-section-number` to outline nodes. Gaps:

| Book format | Structure | Fix |
|-------------|-----------|-----|
| **A** | Nested `<section data-outline-level="…">` | Copy `data-section-number` onto each section’s title heading via new `_section_title_heading_A()` |
| **B** | Flat `<h1>`–`<h3>` export | Headings were already stamped; `.ca-section` wrappers unchanged |

### 2. Display numbers in the iframe (CSS)

`backend.app/assets/book_iframe_highlight.css`:

```css
:is(h1, h2, h3, h4, h5, h6)[data-section-number]::before {
    content: "§ " attr(data-section-number) " — ";
    color: #4a6a5a;
    font-weight: 600;
    font-size: 0.82em;
    letter-spacing: 0.02em;
}
```

Example visible heading: **§ 1.2 — The greenhouse effect** (matches RAG header shape `[§ 1.2 — …]`).

### 3. Single asset injection path

New **`inject_book_viewer_assets()`** in `backend.app/rag/book_document.py` loads the shared CSS + `book_iframe_jump.js` into annotated HTML.

Used by:

- `build_annotated_book_document()` (FastAPI `/book/document`, web client iframe)
- `backend.app/rag/indexing.py` → `get_annotated_book_html()`
- `backend.app/app.py` → `get_annotated_book_html()` (removed ~130 lines of duplicated inline CSS/JS)

Also exported **`package_assets_dir()`** for tests.

## Files changed

| File | Change |
|------|--------|
| `backend.app/html_sectioning.py` | `_section_title_heading_A()`, stamp headings in Format A, docstring |
| `backend.app/assets/book_iframe_highlight.css` | Visible § `::before` rule |
| `backend.app/rag/book_document.py` | `inject_book_viewer_assets()`, `package_assets_dir()` |
| `backend.app/rag/indexing.py` | Use shared injector |
| `backend.app/app.py` | Use shared injector (drop inline duplicate assets) |
| `tests/test_html_sectioning.py` | Fixed imports; new visible-§ tests; removed obsolete `word_chunks` tests |
| `docs/HTML_SECTION_NESTING.md` | Section “Visible section numbers in the viewer” |

## Tests

Run:

```bash
python -m pytest tests/test_html_sectioning.py -v
```

**8 tests**, including:

- `test_annotated_format_a_headings_carry_section_numbers` — nested `<section>` prototype
- `test_annotated_format_b_headings_and_ca_section_wrappers` — flat fixture (`h1` → `1`, `h2` → `1.1`)
- `test_inject_book_viewer_assets_adds_visible_section_css`
- `test_book_iframe_highlight_css_defines_visible_section_rule`

## What stays unnumbered

Same rules as the parser: skippable front-matter `<h1>` ids (`section`, `contents`, …), headings with no body, book title in `<header>` when not a numbered `<section>`.

## Verification (manual)

1. Start Streamlit or API + web client with the student book HTML configured.
2. Open the book iframe — chapter headings should show `§ N —` before the title.
3. Ask a question; click “View source” — citation `§` should match the heading label in the book.

## Related docs

- [`docs/HTML_SECTION_NESTING.md`](../HTML_SECTION_NESTING.md) — outline scheme + visible § pipeline (canonical reference)
- [`input/sample_ca_book.html`](../../input/sample_ca_book.html) — Format A prototype

## Conversation arc

1. User reported: *CA book HTML does not contain visible section numbers.*
2. Investigation: numbers existed only in `data-section-number`, not in rendered text.
3. User asked: *implement fix, write test/s and document it.*
4. Delivered: annotation + CSS + shared injector + tests + `HTML_SECTION_NESTING.md` update.
5. User asked: *save this session to docs/* → this file.
6. User asked: *implement GitHub issue recommendations* → see `docs/github-issues-backlog-2026-05-18.md`.

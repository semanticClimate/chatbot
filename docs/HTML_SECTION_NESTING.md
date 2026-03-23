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

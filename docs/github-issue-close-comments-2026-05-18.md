# GitHub close comments — paste into issues (2026-05-18)

Use after QA on staging/tunnel. Link your PR or commit SHA when posting.

**Before closing:** restart API/Streamlit once (Chroma re-index `para-anchor-v2`) and re-run `python -m encyclopedia.scripts.annotate_cabook` if testing encyclopedia/link fixes.

---

## #24 — CA book HTML does not contain visible section numbers

```
Fixed in [PR/commit].

Headings with `data-section-number` now show a visible prefix in the book iframe, e.g. **§ 1.2 — The greenhouse effect**, via CSS in `climate_streamlit/assets/book_iframe_highlight.css`. Annotation stamps numbers on section title headings (nested and flat HTML).

Docs: `docs/HTML_SECTION_NESTING.md` (section “Visible section numbers in the viewer”), `docs/summary/2026-05-18-visible-section-numbers.md`.

**QA:** Open the student book panel; chapter headings should show `§ N —` before the title. Citations in chat should match those labels.

Closing as fixed. More book HTML issues can be filed separately (see #19, #20, #22).
```

---

## #4 — Source chunk highlight is inconsistent

```
Fixed in [PR/commit] — root cause was **anchor_id skew**, not the jump script.

Format B indexing merged short `<p>` blocks (<40 chars) into one chunk, but annotation assigned one `id` per physical `<p>`. “View source” then highlighted the **preceding** paragraph (matches @petermr’s comment).

**Changes:**
- `climate_streamlit/html_sectioning.py` — one DOM block = one chunk/anchor (no short-paragraph merge in Format B collection).
- `climate_streamlit/rag/indexing.py` — `INDEX_SCHEMA_VERSION = para-anchor-v2` rebuilds Chroma when schema changes.
- Test: `tests/test_html_sectioning.py::test_chunk_anchor_ids_exist_in_annotated_html`.

**QA:** Restart app (re-index). Ask a multi-citation question; each “View source” should land on the cited paragraph.

Please reopen with a specific `anchor_id` / citation if any jump still fails after re-index.
```

---

## #23 — title/tooltips show "Encyclopedia" instead of Wikipedia/Wikidata

```
Fixed in [PR/commit] in `encyclopedia/cabook_annotate/link_normalizer.py`.

- Removed leaking `title="Encyclopedia"` from the encyclopedia container (was inherited by child links).
- Set `title="Wikipedia"` / `title="Wikidata"` on the corresponding link classes; preserve existing article-specific titles from Wikipedia extracts when present.

**QA:** Re-run `python -m encyclopedia.scripts.annotate_cabook`, open prepared encyclopedia + annotated book; hover Wikipedia/Wikidata header links.

Tests: `tests/encyclopedia/test_link_normalizer.py`.
```

---

## #22 — CA book has unresolved Wikipedia links

```
Partially fixed in [PR/commit] — pipeline now **demotes** encyclopedia entry header links when `data-first-paragraph-retrieved="false"` (replaced with `<span class="no-wikipedia">` instead of linking to empty Wikipedia pages).

**Still content/upstream:** ~35 AMI entries lack a real article; footnotes in the raw book may still point at bad URLs until source HTML is cleaned. See `docs/github-issues-backlog-2026-05-18.md`.

**QA:** Re-run annotation pipeline; open encyclopedia entries known to be missing Wikipedia text — header should not be a dead link.

File new issues for specific terms or footnote URLs that still 404.
```

---

## #19 — hyperlinks in book coinciding with links have no text

```
Fixed in [PR/commit] — encyclopedia phrase matcher was breaking footnote-adjacent text (e.g. “Do [139]…”).

**Changes:**
- Skip annotation inside footnote refs / footnotes sections (`html_annotator.py`).
- Do not match pure numeric phrases (`phrase_matcher.py`).
- `min_term_length = 3` in `annotate_cabook.toml`.

**QA:** Re-run `python -m encyclopedia.scripts.annotate_cabook`; check passage around former fn139 scramble (~“Do Chemistry teachers…” / Dalton footnote).

Expect **more** book/HTML bugs as we review — please file with section § number + screenshot.
```

---

## #13 — failed chatbot replies should drop down to encyclopedia

```
Implemented in [PR/commit] — when retrieval is empty or all results are weaker than `max_distance`, the bot returns a **multilingual hint** to use encyclopedia links in the book instead of calling the LLM on poor context.

`climate_streamlit/llm/ask.py` — see `_ENCYCLOPEDIA_HINT` and `_retrieval_is_weak()`.

**QA:** Ask something off-topic or very far from book wording; expect encyclopedia guidance (en/fr/es/pt/hi per chat language).

Future: dedicated encyclopedia RAG collection (not in this change). Closing as the requested fallback behaviour for weak book retrieval.
```

---

## #16 — Mobile responsiveness: images squeezed

```
Fixed in [PR/commit] in `climate_streamlit/assets/book_iframe_highlight.css`:

- `img { height: auto; object-fit: contain; … }`
- `figure img { width: 100%; }`

**QA:** Open tunnel URL on a phone; Student Book images should keep aspect ratio (may letterbox slightly — preferable to horizontal squeeze).

Reopen if a specific figure still looks wrong (§ number + screenshot).
```

---

## Template — new book bug (copy for future issues)

```
**Book bug** — [short title]

**§ section:** (visible § label or heading text, e.g. § 3.2 — …)
**Location:** chapter / heading name
**Expected:**
**Actual:** (screenshot if UI)
**Format:** Streamlit / web client / annotated HTML file
**Notes:** footnote #, image filename, link URL, etc.

Found while QA after 2026-05-18 book fixes — not a duplicate of #4/#19/#20/#22 unless same spot.
```

Suggested label: `book-content` or `bug` + `book-viewer`.

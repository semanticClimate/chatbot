# GitHub issues backlog — actions (2026-05-18)

Repository: [semanticclimate/chatbot](https://github.com/semanticclimate/chatbot)

This document maps open issues to implementation status after the 2026-05-18 engineering pass.

## Implemented in codebase

| Issue | Title | What we did |
|-------|--------|-------------|
| [#24](https://github.com/semanticClimate/chatbot/issues/24) | Visible § section numbers | `annotate_html_with_section_ids` + `book_iframe_highlight.css` — see `docs/summary/2026-05-18-visible-section-numbers.md` |
| [#4](https://github.com/semanticClimate/chatbot/issues/4) | Source highlight inconsistent | Format B indexing no longer merges short `<p>` nodes; `INDEX_SCHEMA_VERSION` forces Chroma re-index; test `test_chunk_anchor_ids_exist_in_annotated_html` |
| [#23](https://github.com/semanticClimate/chatbot/issues/23) | Wrong link tooltips | `link_normalizer`: strip container `title="Encyclopedia"`, set Wikipedia/Wikidata titles |
| [#22](https://github.com/semanticClimate/chatbot/issues/22) | Unresolved Wikipedia links | Demote header links when `data-first-paragraph-retrieved="false"` to `<span class="no-wikipedia">` |
| [#19](https://github.com/semanticClimate/chatbot/issues/19) | Footnote / link collisions | Skip phrase match on digits; skip footnote contexts; `min_term_length = 3` |
| [#13](https://github.com/semanticClimate/chatbot/issues/13) | Encyclopedia fallback | `ask_groq` returns multilingual hint when retrieval is empty/weak |
| [#16](https://github.com/semanticClimate/chatbot/issues/16) | Mobile images squeezed | `book_iframe_highlight.css`: `object-fit: contain`, `height: auto` on `img` |

## Still open (needs follow-up)

| Issue | Title | Recommended next step |
|-------|--------|------------------------|
| [#21](https://github.com/semanticClimate/chatbot/issues/21) | Cloudflare via NIPGR | Institutional network — see `docs/installation/nipgr-cloudflare-notes.md` |
| [#20](https://github.com/semanticClimate/chatbot/issues/20) | Wrong image (Great Cropping Out) | **Content:** Picture B reuses `image46.jpeg`; need cropped AP asset or use distinct file — see note in that doc |
| [#3](https://github.com/semanticClimate/chatbot/issues/3) | Ollama not running | Zoom summary app only — document `ollama serve` or add graceful UI message if app is restored |
| [#2](https://github.com/semanticClimate/chatbot/issues/2) | Matthew’s vision | Keep as epic — see `docs/epics/matthew-bot-vision.md` |
| [#8](https://github.com/semanticClimate/chatbot/issues/8) | Q&R table export | Feature epic — see `docs/epics/query-response-export.md` |

## Ops after deploy

1. **Re-index Chroma** — first API/Streamlit start after upgrade rebuilds when `index_schema_version` ≠ `para-anchor-v2`.
2. **Re-run encyclopedia pipeline** — `python -m encyclopedia.scripts.annotate_cabook` (shows stage lines + `annotate` progress bar on stderr; ~1–2 min after phrase pre-compile fix).
3. **Close issues #4, #13, #16, #19, #22, #23, #24** on GitHub after QA on tunnel/staging.

## Suggested labels (manual on GitHub)

- `bug`: #4, #19, #20, #22, #23  
- `enhancement`: #13, #8, #2  
- `deployment`: #21  
- `book-viewer`: #4, #16, #24  
- `encyclopedia`: #13, #19, #22, #23  

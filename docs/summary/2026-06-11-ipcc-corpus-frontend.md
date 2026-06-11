# Session summary — IPCC corpus, frontend rename, multi-corpus config

**Date:** 2026-06-11 (system date of generation)

This document records decisions and implementation from a working session on building an IPCC-based chatbot, comparing corpora, and refactoring the repo for config-driven source switching and frontend naming.

---

## 1. Style guides (session start)

Read and adopted conventions from sibling repos:

| Source | Path |
|--------|------|
| Primary | `../pygetpapers/docs/styleguide.md` |
| amilib extensions | `../amilib/docs/style_guide_compliance.md` |
| Corpus-specific | `../amilib/docs/corpus/style_compliance.md` |

Notable rules for future work: absolute imports, `Path(a, b, c)` construction, external config/CSS files, assert-based tests, explicit user approval before code changes, always verify system date via `date`.

---

## 2. IPCC SYR semantic HTML (amilib test resources)

**Confirmed location** (Longer Report — the only SYR section with numbered paragraph IDs today):

```
../amilib/test/resources/ipcc/syr/longer-report/html_with_ids.html
```

Mirror: `../amilib/test/resources/ipcc/cleaned_content/syr/longer-report/html_with_ids.html`

**Supporting files** (same directory):

- `id_list.html` — 204 anchor links
- `para_list.html` — paragraphs extracted with IDs
- `de_gatsby.html` — semantic HTML before ID injection (~415 `<p>` tags)

**Paragraph ID scheme:** `{section}_p{N}` (e.g. `2.1.1_p1`, `1. Introduction_p1`). IDs are assigned by amilib’s `add_para_ids_and_make_id_list()` in `test/ipcc_classes.py`.

**Semantic structure:** `h1-container`, `h2-container`, `h3-container` with section IDs matching report numbering.

**Not yet usable:** SPM, Technical Summary, glossary, and acronyms under `cleaned_content/syr/*/html_with_ids.html` are 404/error pages (0 paragraph IDs). Raw sources exist under `syr/spm/` etc. but need processing.

---

## 3. CABook vs SYR Longer Report — relative sizes

| Metric | CABook | SYR Longer Report | Ratio (CABook ÷ SYR) |
|--------|--------|-------------------|------------------------|
| HTML file size | ~995 KB | ~564 KB | ~1.8× |
| Estimated words | ~142,000 | ~49,000 | ~2.9× |
| `<p>` tags | 3,527 | 417 | ~8.5× |
| RAG paragraph units | 4,552 chunks | 204 numbered IDs (~192 indexed after min-length filter) | ~22× |

CABook paths: `input/full_student_book.html`, Chroma `chroma_db`, collection `climate_academy_paragraphs_v2`.

**Implication:** an IPCC SYR chatbot corpus is roughly one-third the text and far fewer retrievable units than CABook; Chroma index will be smaller if using the same embedding model.

---

## 4. Product direction

Agreed direction: build a chatbot from IPCC (starting with Longer Report), reusing the existing FastAPI + browser UI pattern established for CABook.

Stack (post-refactor):

| Layer | Location |
|-------|----------|
| Frontend | `frontend/` (static HTML/CSS/JS) |
| API | `fastapi_app/main.py` → `climate_streamlit/api_server.py` |
| RAG / config | `climate_streamlit/` |

Legacy Streamlit (`climate_streamlit/app.py`) is optional; not the deployment path.

---

## 5. Implementation — frontend rename

Renamed **`web_client/` → `frontend/`** and updated operational docs/scripts:

- `scripts/start_remote_test.sh`
- `docs/installation/start-quick-tunnel.sh`, `stop-quick-tunnel.sh`, `start-quick-tunnel.ps1`
- `docs/installation/mac-quick-tunnel-runbook.md`, `windows-quick-tunnel-runbook.md`
- `README.md`, `frontend/README.md`
- `.gitignore` — `frontend/tunnel-api-base.txt`
- Cursor rule: `.cursor/rules/frontend-browser-constraints.mdc` (replaces `web-client-browser-constraints.mdc`)

**localStorage:** primary key `climate_frontend_api_base`; migrates from legacy `climate_web_client_api_base` on read.

---

## 6. Implementation — multi-corpus config

**Config file:** `climate_streamlit/config/app.defaults.toml`

| Profile | Document | HTML | Chroma dir | Collection |
|---------|----------|------|------------|------------|
| `cabook` (default) | Climate Academy Student Book | `input/full_student_book.html` | `chroma_db` | `climate_academy_paragraphs_v2` |
| `ipcc_syr` | IPCC AR6 SYR Longer Report | `../amilib/test/resources/ipcc/syr/longer-report/html_with_ids.html` | `chroma_db_ipcc_syr` | `ipcc_syr_paragraphs_v1` |

**Switch at API startup:**

```bash
export CLIMATE_CORPUS_PROFILE=ipcc_syr   # or cabook
python -m uvicorn fastapi_app.main:app --host 127.0.0.1 --port 8800
```

**Optional:** `CLIMATE_CONFIG_PATH=/path/to/custom.toml`

Each profile has its own: `html`, `pdf`, `chroma_dir`, `collection_name`, `html_format`, `system_prompt`, and `[corpora.<id>.ui]` copy.

**Code touched:**

- `climate_streamlit/config_loader.py` — profile loading; fields `corpus_id`, `corpus_label`, `html_format`, `system_prompt_path`
- `climate_streamlit/html_sectioning.py` — IPCC format (`*_pN` ids, `h*-container` sections)
- `climate_streamlit/prompts/system_rag_ipcc_json.txt` — IPCC system prompt
- `climate_streamlit/rag/indexing.py`, `book_document.py`, `llm/prompts.py`, `llm/ask.py` — wired to profile settings
- `climate_streamlit/api_server.py` — `GET /corpus`; `/ready` includes corpus info
- `frontend/js/api.js` — `getCorpus()` helper

**Run frontend:**

```bash
cd frontend && python -m http.server 8081
```

**Smoke checks:**

```bash
curl -s http://127.0.0.1:8800/health
curl -s http://127.0.0.1:8800/ready
curl -s http://127.0.0.1:8800/corpus
```

Restart the API after changing `CLIMATE_CORPUS_PROFILE`. First run with a new profile builds that profile’s Chroma index.

---

## 7. Adding a new corpus profile (checklist)

1. Add `[corpora.<id>]` block in `app.defaults.toml` (paths, collection, `html_format`, UI, `system_prompt`).
2. If HTML structure differs, extend `html_sectioning.py` or set `html_format` to `cabook` / `ipcc` / extend parser.
3. Add system prompt under `climate_streamlit/prompts/` if needed.
4. Use a **separate** `chroma_dir` and `collection_name` per profile.
5. Document in `frontend/README.md` and this file if operational steps change.

---

## 8. Open / follow-on work

- [ ] First full IPCC index + manual QA via `frontend/` with `CLIMATE_CORPUS_PROFILE=ipcc_syr`
- [ ] Frontend: surface active corpus label from `GET /corpus` in UI chrome
- [ ] Process SPM / Technical Summary / annexes when IPCC sources are available
- [ ] IPCC-specific example questions in `frontend/js/examples_data.js`
- [ ] Consider symlink or copy of SYR HTML into `input/` if `../amilib` path is fragile on other machines

---

## 9. Git merge note (earlier in session, not implemented here)

User had an in-progress `git merge frontend` with `MERGE_HEAD` set. Resolution options documented in chat: finish with `git checkout --theirs . && git add -A && git commit`, or `git merge --abort`. Not part of this doc’s code changes.

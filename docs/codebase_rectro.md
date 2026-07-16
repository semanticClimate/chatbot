# Deep Technical Refactor Diary for the Climate Chatbot Codebase

## Scope and method

This document compares the original `chatbot_1.7.2026` archive with the refactored `chat_refactored.16.7.26` archive and records the refactoring journey as a technical diary.

To keep the analysis honest and useful, I ignored:
- `__pycache__`
- `.pyc` files
- bundled virtual-environment internals
- generated binary vector files inside Chroma index directories
- bulk media assets where they do not affect architecture

The comparison still leaves a large and meaningful codebase:
- the original archive contains far more files because it includes the bundled environment and many generated assets
- excluding the bundled environment, the original project has **76 Python files**
- the refactored project has **80 Python files**
- the refactored project is architecturally smaller in top-level complexity even though it has slightly more Python modules, because responsibility has been split more cleanly

### Key file-size shifts

A few modules capture the refactor direction very clearly:

| Module | Old size | New size | What changed |
|---|---:|---:|---|
| `climate_streamlit/app.py` | 1275 lines | split across backend + frontend | a monolithic UI/logic file became a layered architecture |
| `climate_streamlit/api_server.py` | 405 lines | `backend/app/main.py` (102 lines) + route modules | server startup and endpoints were separated |
| `climate_streamlit/api_client.py` | 54 lines | frontend JS API modules | browser-side API interaction moved to the client |
| `climate_streamlit/html_sectioning.py` | 874 lines | wrapper + `html_sectioning_core/*` | one giant parser became a focused multi-file package |
| `climate_streamlit/llm/ask.py` | 275 lines | `backend/app/llm/ask.py` | mostly relocated, but now under backend ownership |
| `climate_streamlit/pdf/index.py` | 130 lines | `backend/app/pdf/index.py` | preserved logic, cleaner package placement |
| `climate_streamlit/rag/retrieve.py` | 48 lines | `backend/app/rag/retrieve.py` | retrieval stayed compact and was moved into backend scope |

The big story is not “files moved.” The big story is **responsibilities were broken apart and assigned to clearer layers**.

---

# Day 1 – Baseline analysis of the original architecture

The original project was centered around `climate_streamlit`, and that package carried too many unrelated concerns.

## What lived together in the old layout

The old package included:
- Streamlit application code
- FastAPI server logic
- API client logic
- RAG indexing and retrieval
- LLM prompting and parsing
- PDF search and PDF rendering
- HTML sectioning and book annotation
- conversation state handling
- configuration loading
- database helpers
- UI widgets and styling
- zoom-summary utilities

That meant a single package had to support:
1. application startup
2. browser UI rendering
3. chat orchestration
4. retrieval
5. encyclopedia serving
6. PDF handling
7. data logging
8. configuration access

## Why that was a problem

The structure was functional, but it was hard to debug. If a response failed, you had to ask:
- is the issue in the UI?
- the server?
- the retriever?
- the HTML parser?
- the encyclopedia source?
- the PDF index?
- the conversation serializer?

This is exactly the kind of codebase that starts “fine” and becomes painful once the feature count grows.

## Important old files

Two files were especially important:
- `climate_streamlit/app.py` — **1275 lines**
- `climate_streamlit/api_server.py` — **405 lines**

Those files carried too much responsibility for their size.

## Outcome

The refactor goal was defined as: **preserve behaviour while reducing structural complexity**.

---

# Day 2 – Planning the backend split

The second stage was architectural planning, not just file moving.

## What needed to change

The codebase needed a backend that could own:
- server startup
- route definitions
- request validation
- orchestration
- retrieval
- conversation persistence
- LLM interaction
- configuration and runtime paths

## Old problem pattern

In the original layout, the server module had grown into a “god file.” Even where helper functions existed, the deployment entry point and the request logic were still too tightly coupled.

## Refactor direction

The backend was split conceptually into:
- `main.py` as the composition root
- `api/` for request endpoints and schemas
- `routes/` for feature-specific route modules
- `services/` for orchestration
- `rag/` for retrieval and knowledge-base handling
- `llm/` for model-side work
- `pdf/` for search/render helpers
- `config/` for path and settings management
- `database/` for logging and persistence helpers
- `utils/` for HTML sectioning support

## Outcome

The project moved from “one package does everything” to **layered backend ownership**.

---

# Day 3 – Creating the backend composition root

This day is where the backend stopped being abstract and became concrete.

## New entry point

The refactored backend centers on:
- `backend/app/main.py`

This file is only **102 lines**, which is a major reduction in role density compared with the old server-side entry point.

## What `main.py` now does

From the refactored file:
- creates the FastAPI app
- loads settings at startup
- initializes the Chroma knowledge base
- loads the Groq client
- configures CORS
- mounts static book media
- includes routers
- runs the app when executed directly

So `main.py` is now a **composition root**, not a “put everything here” script.

## Important implementation details

The current file still contains a runtime block that calls:
- `uvicorn.run("fastapi_app.main:app", ...)`

That string looks like a legacy launch target, because the refactored archive no longer contains a `fastapi_app/` package. That is the kind of detail that matters in real refactors: the code may be structurally clean but still retain an old entry-point string.

## Outcome

The backend became easier to reason about because app assembly was separated from endpoint logic.

---

# Day 4 – Extracting API responsibilities into smaller units

This stage focused on the API layer.

## Old state

`climate_streamlit/api_server.py` contained many API concerns together:
- request models
- endpoint definitions
- health checks
- logs export
- readyness checks
- encyclopedia serving
- book serving
- retrieval endpoint
- ask endpoint
- conversation import/export

## New state

The API layer is now split across:
- `backend/app/api/ask.py`
- `backend/app/api/models.py`
- `backend/app/api/routes/books.py`
- `backend/app/api/routes/chat.py`
- `backend/app/api/routes/conversation.py`
- `backend/app/api/routes/encyclopedia.py`
- `backend/app/api/routes/health.py`

## Why this matters

This split is not cosmetic. It means feature areas are no longer forced to share one file:
- `ask.py` handles the ask request path and request validation
- `models.py` keeps request schemas separate
- `routes/books.py` owns book-outline and book document endpoints
- `routes/chat.py` handles retrieval-related chat routing
- `routes/conversation.py` owns import/export of conversations
- `routes/encyclopedia.py` handles encyclopedia content and proxying
- `routes/health.py` handles root, health, ready, and logs export

## Old-to-new route mapping

The old `api_server.py` functions were split from a single module into dedicated routes:

- `root()` → `routes/health.py`
- `health()` → `routes/health.py`
- `logs_export_csv()` → `routes/health.py`
- `ready()` → `routes/health.py`
- `book_outline()` → `routes/books.py`
- `book_document()` → `routes/books.py`
- `book_jump()` → `routes/books.py`
- `encyclopedia_empty()` → `routes/encyclopedia.py`
- `encyclopedia_entry()` → `routes/encyclopedia.py`
- `proxy_external()` → `routes/encyclopedia.py`
- `retrieve_ep()` → `routes/chat.py`
- `ask_ep()` → `backend/app/api/ask.py`
- `conversation_import_ep()` / `conversation_import_csv()` → `routes/conversation.py`

## Outcome

The API layer became more maintainable because each route family now has a small, obvious home.

---

# Day 5 – Splitting request handling from orchestration

This day is about the difference between **receiving a request** and **doing the work**.

## Old situation

The server layer previously did too much directly:
- parsed request payloads
- normalized conversation objects
- called retrieval
- called the model
- appended turns
- logged interactions
- returned response structures

That is a lot of coordination to keep inside one file.

## New structure

The request-handling path now lives in:
- `backend/app/api/ask.py`

That file is only **96 lines**, and its job is mostly to:
- validate input
- call the service layer
- append the new turn
- log the interaction if needed
- return structured output

The request and schema definitions are isolated in:
- `backend/app/api/models.py` (**59 lines**)

## Why that helps

This separation makes the API easier to test:
- models can be validated independently
- route behavior can be checked without looking at lower-level retrieval details
- orchestration logic can be changed without changing the request schema

## Outcome

The API is now more modular and less likely to become another giant all-in-one file.

---

# Day 6 – Extracting chat orchestration into services

This stage focused on separating orchestration from the endpoint layer.

## Relevant modules

The refactored backend contains:
- `backend/app/services/chat_service.py`
- `backend/app/services/conversation.py`

## What the service layer does

These modules coordinate:
- retrieval invocation
- model invocation
- conversation normalization
- turn appending
- CSV/JSON conversion of conversation data

This is the right place for that work because services are the “glue” between API, retrieval, and persistence.

## Old versus new

In the old codebase, these ideas were close to the server code and mixed with other concerns.

In the refactored codebase:
- route modules only handle HTTP-facing behavior
- service modules handle application behavior
- data conversion is isolated from the API layer

## Outcome

The service layer now reads like a coordination layer instead of a dump of mixed functionality.

---

# Day 7 – Organizing RAG, indexing, and document rendering

This is one of the most important refactor areas because retrieval is core to the application.

## RAG modules in the new codebase

The refactored backend keeps retrieval-related work in:
- `backend/app/rag/retrieve.py`
- `backend/app/rag/indexing.py`
- `backend/app/rag/book_document.py`
- `backend/app/rag/encyclopedia_document.py`
- `backend/app/rag/sources.py`

## What was preserved

The actual retrieval pipeline stayed compact:
- `retrieve.py` is still **48 lines**
- its role is still focused on retrieval rather than orchestration

## What changed more deeply

`indexing.py` now acts like the backend knowledge-base builder:
- loads the embedder
- creates or opens the Chroma collection
- checks index schema version
- reads the HTML book
- parses it into chunks
- batches embeddings into Chroma

The new function `build_knowledge_base_core()` lives here, which is a clean separation from UI concerns.

## Why the split is good

The old code had knowledge-base creation tied more closely to the application flow. The new structure makes the retrieval system reusable and easier to test without Streamlit runtime dependencies.

## Outcome

The retrieval pipeline is now grouped in a way that makes sense for a RAG system: indexing, retrieval, documents, and source handling are all in one backend area.

---

# Day 8 – Splitting the PDF utilities from the rest of the app

The PDF logic was already separated in the old code, but the refactor preserved and clarified that separation.

## Relevant files

Old:
- `climate_streamlit/pdf/index.py`
- `climate_streamlit/pdf/text.py`
- `climate_streamlit/pdf/viewer.py`

New:
- `backend/app/pdf/index.py`
- `backend/app/pdf/text.py`
- `backend/app/pdf/viewer.py`

## Function-level meaning

### `pdf/index.py`
Handles:
- loading the PDF index
- caching
- mapping chunks to PDF pages/blocks

### `pdf/text.py`
Handles:
- search query construction
- normalization helpers
- keyword extraction

### `pdf/viewer.py`
Handles:
- loading PDF as data URI
- rendering the PDF viewer

## Why this still matters in the refactor

The benefit is not only that these files exist, but that they now sit under the backend package with the rest of the logic they support. That makes the overall architecture more coherent.

## Outcome

The PDF layer remained separate, but the package placement now matches the rest of the backend structure.

---

# Day 9 – Extracting book-document rendering and local asset handling

This stage focused on the HTML book document pipeline.

## New module

The refactored code places this work in:
- `backend/app/rag/book_document.py`

## What it handles

This module now covers:
- local image inlining
- book HTML path resolution
- asset injection for the viewer
- annotated book document generation

## Why this matters

The book viewer is not just a display widget. It is part of the retrieval experience because the user interacts with highlighted content, annotations, and linked media.

Moving this logic out of the main app file removes a lot of clutter from the application entry points.

## Outcome

Book document rendering became a dedicated backend responsibility instead of a large utility block embedded in the application file.

---

# Day 10 – Reorganizing the frontend into explicit client-side modules

The frontend was not just moved. It was decomposed.

## Old frontend layout

The old web client lived under:
- `web_client/`

It contained:
- `index.html`
- CSS files
- image assets
- docs
- JS files such as `main.js`, `api.js`, `render.js`, `state.js`, `ui_modals.js`, `ui_strings.js`, `examples.js`, `examples_data.js`, `help.js`, `lang_prefs.js`

## New frontend layout

The refactored frontend lives under:
- `frontend/`

It contains:
- `index.html`
- `css/`
- `assets/images/`
- `docs/`
- a more modular `js/` tree

## JS modularization in the new frontend

The new client code is split into:
- `frontend/js/app.js`
- `frontend/js/api/api.js`
- `frontend/js/api/chat.js`
- `frontend/js/core/api_base.js`
- `frontend/js/core/dom.js`
- `frontend/js/features/book.js`
- `frontend/js/features/chat.js`
- `frontend/js/features/sidebar.js`
- `frontend/js/features/tooltip.js`
- `frontend/js/state/state.js`
- `frontend/js/ui/render.js`
- `frontend/js/ui/ui_modals.js`
- `frontend/js/ui/ui_strings.js`
- `frontend/js/help.js`
- `frontend/js/lang_prefs.js`
- `frontend/js/data/examples_data.js`
- `frontend/js/examples/examples.js`

## Why this is better

Compared with the older `web_client/js/main.js` style, the new structure makes it easier to change one area without risking the rest of the client.

The frontend is now split by role:
- core utilities
- API calls
- feature behavior
- UI rendering
- state
- examples
- help
- language preferences

## Outcome

The frontend became a real client-side application structure, not just a collection of static files.

---

# Day 11 – Centralizing data, configuration, and HTML sectioning internals

This day covers the support code that quietly powers the application.

## Data layout

The original project scattered runtime resources at the top level:
- `encyclopedia/`
- `chroma_db/`
- `input/`

The refactored version centralizes them under:
- `data/chroma_db/`
- `data/input/`
- `data/encyclopedia/`

## Why that is important

This simplifies:
- deployment
- backup
- path resolution
- configuration management
- reproducibility

## Encyclopedia source and output paths

The new encyclopedia document code makes the data structure explicit:

- `prepared_encyclopedia_path()` → `data/encyclopedia/source/CA_encyclopedia_new.html`
- `annotated_book_path()` → `data/encyclopedia/output/full_student_book_annotated.html`
- `link_css_path()` → `data/encyclopedia/assets/cabook_links.css`

That shows the refactor has a defined source/output split rather than a vague “some data folder.”

## HTML sectioning refactor

This is one of the deepest technical changes.

### Old state
The original `climate_streamlit/html_sectioning.py` was **874 lines** and contained:
- parsing
- chunking
- annotation
- numbering
- prompt formatting
- book-path parsing

### New state
That logic is split into:
- `backend/app/utils/html_sectioning.py` — compatibility facade
- `backend/app/utils/html_sectioning_core/annotation.py`
- `backend/app/utils/html_sectioning_core/chunking.py`
- `backend/app/utils/html_sectioning_core/constants.py`
- `backend/app/utils/html_sectioning_core/helpers.py`
- `backend/app/utils/html_sectioning_core/legacy.py`
- `backend/app/utils/html_sectioning_core/models.py`
- `backend/app/utils/html_sectioning_core/numbering.py`
- `backend/app/utils/html_sectioning_core/parsing.py`

## Why this is a real improvement

The old parser had too many responsibilities in one place. The new version makes the responsibilities visible:
- parsing book structure
- chunking text
- numbering sections
- annotation
- backwards-compatible legacy helpers

The facade keeps the old import path alive while the core logic becomes independently maintainable.

## Outcome

This is one of the clearest examples of a serious refactor, because the logic was not merely moved; it was decomposed by responsibility.

---

# Day 12 – Testing and documentation alignment

A refactor is only convincing if it survives testing.

## Tests in the project

The refactored archive still contains a test suite, including:
- `test_ask_encyclopedia_fallback.py`
- `test_encyclopedia_document.py`
- `test_html_sectioning.py`
- `test_zoom_daily_summary.py`
- `test_zoom_daily_summary_integration.py`
- `test_zoom_daily_summary_watch.py`
- `test_zoom_slack.py`

## What testing tells us

This is important because the refactor changed:
- import paths
- runtime data paths
- module ownership
- route layout
- frontend structure

If the code still passes the same kinds of tests, that is a sign the refactor preserved behaviour while changing structure.

## Documentation update

Documentation also needed to reflect the new architecture:
- backend/frontend split
- data layout
- route modules
- test structure
- new path conventions

## Outcome

The project is now structured in a way that is easier to explain, maintain, and test.

---

# Day 13 – Regression investigation and final architecture comparison

This final day documents the regression and the most important old-vs-new comparison.

## Regression found

During post-refactor testing, encyclopedia content was no longer displayed in the application.

## What was observed

The debugging process used print statements to trace the retrieval path. The pipeline still executed, which means the regression was not a total failure of the encyclopedia feature. The problem was more likely that the application was resolving the wrong source path or configuration.

## Most probable cause

The most likely explanation is a **path-resolution mismatch** introduced during the directory reorganization.

The refactored code explicitly defines encyclopedia paths under:
- `data/encyclopedia/source/CA_encyclopedia_new.html`

So if the runtime log showed the application using `data/input/`, that suggests one of the following:
- an older path was still being referenced somewhere
- a different code path was used during execution
- a config value was pointing at the wrong directory
- a data-root override was interfering with the expected encyclopedia path

That is the correct level of certainty: the evidence supports a path mismatch, but it does not justify pretending the exact root cause is already fully proven.

## Old folder structure

```text
chatbot_1.7.2026/
    climate_streamlit/
        app.py
        api_server.py
        api_client.py
        rag/
        llm/
        pdf/
        ui/

    encyclopedia/
    chroma_db/
    input/
    docs/
    web_client/
    tests/
```

## New folder structure

```text
chat_refactored.16.7.26/
    backend/
        app/
            api/
            api/routes/
            services/
            rag/
            llm/
            pdf/
            config/
            database/
            utils/

    frontend/
        css/
        js/
        assets/
        docs/

    data/
        chroma_db/
        input/
        encyclopedia/

    tests/
```

## Responsibility comparison

| Area | Old layout | New layout |
|---|---|---|
| App composition | mostly inside `climate_streamlit/app.py` | `backend/app/main.py` + smaller modules |
| API server | large `api_server.py` | `api/ask.py` + `api/routes/*` |
| Request models | mixed into server code | `api/models.py` |
| Retrieval | package-level but tightly coupled | `backend/app/rag/*` |
| HTML sectioning | single 874-line file | facade + core package split by responsibility |
| Frontend JS | smaller `web_client/js/` bundle | more explicit modular frontend tree |
| Data files | scattered across top-level folders | centralized under `data/` |
| Tests | present but alongside older structure | dedicated `tests/` directory |
| Encyclopedia source | mixed with older data layout | explicit source/output paths under `data/encyclopedia/` |

## Conclusion

The refactor is not trivial. It is a meaningful architectural rewrite that:
- separates concerns
- reduces monolithic modules
- clarifies path handling
- improves maintainability
- improves long-term debugging

The encyclopedia regression is not a sign that the refactor was “bad.” It is a normal and useful regression to document because it shows the project was tested after the structural changes. The most likely issue is a path mismatch introduced by the new data organization, especially around encyclopedia source resolution.

---

# Final note

This diary is intentionally technical, but it stays careful about what is actually observed versus what is inferred. That is the right balance for refactor documentation: deep enough to be useful, but not so aggressive that it invents certainty where there is only evidence.

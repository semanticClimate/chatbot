## Technical Guide to the Backend Architecture

### Purpose

This document explains the backend side of the refactored climate chatbot codebase in a way that should be useful to a new intern or first-time contributor. It focuses on the actual responsibilities of the backend modules, the main functions in each area, and the way the pieces fit together at runtime.

The backend is the part of the system that handles:
- application startup
- API routing
- retrieval-augmented generation (RAG)
- language-model interaction
- PDF and HTML document processing
- conversation normalization and export
- persistence and logs
- configuration and file-path resolution

The main backend entry point is:

- `backend/app/main.py`

The backend architecture is intentionally layered so that a change in one area does not require editing one giant script.

---

## 1. Backend overview

The backend is organized under `backend/app/` and split into focused packages:

- `api/` — HTTP request handling, schemas, and routes
- `services/` — orchestration logic that connects API, retrieval, model calls, and conversation handling
- `rag/` — retrieval, indexing, and document preparation
- `llm/` — Groq completion flow and response parsing
- `pdf/` — PDF indexing, search helper logic, and viewer support
- `config/` — settings and path resolution
- `database/` — SQLite log storage and feedback handling
- `utils/` — HTML sectioning and compatibility helpers
- `assets/` — CSS/JS used by the backend-rendered book and encyclopedia views

The backend also depends heavily on the `data/` directory, which stores:
- ChromaDB files
- book HTML input files
- encyclopedia source/output files
- media files used by the book viewer

---

## 2. Startup flow: `backend/app/main.py`

### File role

`main.py` is the backend composition root. It does not try to implement all application logic itself. Instead, it wires together the app and loads the shared runtime objects needed by the route handlers.

### Main functions

#### `lifespan(app: FastAPI)`
This async lifespan handler performs startup initialization:

- loads settings via `get_settings()`
- stores settings in `app.state.settings`
- builds or loads the Chroma knowledge base through `build_knowledge_base_core()`
- stores the resulting collection and embedder in `app.state.collection` and `app.state.embedder`
- loads the Groq client using `load_groq_from_env()`
- yields control to allow the FastAPI app to serve requests

This is important because many route handlers expect these objects to already exist on `app.state`.

#### `_cors_origins()`
This helper reads the `CLIMATE_API_CORS_ORIGINS` environment variable and returns the allowed origins list.

- `"*"` means all origins are allowed
- comma-separated values are split and trimmed
- empty entries are removed

### Additional runtime behavior

`main.py` also:
- creates the FastAPI application
- installs CORS middleware
- mounts `/book/media` as a static directory
- includes routers for health, chat, books, encyclopedia, conversation, and ask endpoints

### Important note

The `__main__` launch block currently runs:

- `uvicorn.run("fastapi_app.main:app", ...)`

That string looks like a legacy launch target. It is worth checking during deployment because the refactored package is under `backend.app`, not `fastapi_app`.

---

## 3. Configuration: `backend/app/config/settings.py`

This module is the central place for resolved paths and application settings.

### Main functions and classes

#### `SidebarLabels`, `PanelLabels`, `ChatHistoryUi`, `MessageCopy`
These dataclasses group UI copy and label strings together so they can be loaded as structured settings.

#### `AppSettings`
This frozen dataclass stores the main runtime configuration, including:
- root directory
- data paths
- HTML path
- Chroma directory
- encyclopedia paths
- UI labels
- top-k retrieval settings
- max-distance cutoff for retrieval
- other default values

#### `_resolve_path()`
Normalizes a configured path relative to a root directory.

#### `get_settings()`
Loads `config/app.defaults.toml`, resolves the paths, and returns an `AppSettings` object. This function is cached so the backend can reuse the same configuration object.

### Why this matters

If a path changes during refactoring, this module is one of the first places to inspect. It is likely to be involved in any regression involving:
- wrong input directory
- missing encyclopedia file
- Chroma directory mismatch
- bad HTML path resolution

---

## 4. API layer

The API layer is split into a light request module and a set of route modules.

### 4.1 `backend/app/api/ask.py`

This file handles the `/ask` endpoint.

#### Main functions/classes

##### `AskRequest`
A request schema that contains:
- `question`
- `conversation`
- `top_k`
- `response_language`

##### `ask_ep()`
This is the main request handler for the chat question endpoint.

It:
- receives the incoming question
- normalizes the conversation payload
- calls the service layer
- appends the assistant turn
- returns response data in a structured JSON format

This file should stay small. If it starts doing retrieval, parsing, logging, or formatting directly, that is a sign the refactor boundaries are being violated.

---

### 4.2 `backend/app/api/models.py`

This module stores API models and request/response schemas. Keeping these separate from route logic makes the API easier to validate and easier to extend.

### 4.3 Route modules under `backend/app/api/routes/`

#### `books.py`
This module handles book-related endpoints.

Main functions:
- `_cached_book_outline()`
- `_cached_book_html()`
- `book_outline()`
- `book_document()`
- `book_jump()`

Typical responsibilities:
- serve the book outline
- provide the annotated book document
- support jumps from source references into the book viewer

#### `chat.py`
This module handles chat-related retrieval entry points.

Main function:
- `retrieve_ep()`

This route is responsible for returning retrieval data for the frontend, without combining it with the full completion pipeline.

#### `conversation.py`
This module handles conversation import/export.

Main functions typically include:
- import from JSON-like conversation payloads
- import from CSV text
- export conversation as JSON or CSV

The implementation relies on:
- `normalize_conversation()`
- `conversation_from_csv()`
- `conversation_to_csv()`
- `conversation_to_json_bytes()`

#### `encyclopedia.py`
This module handles encyclopedia content and proxy behavior.

Main functions:
- `_cached_encyclopedia_placeholder()`
- `encyclopedia_empty()`
- `encyclopedia_entry()`
- `proxy_external()`

This is one of the most important backend modules for the regression you observed. It depends on:
- `prepared_encyclopedia_path()`
- `annotated_book_path()`
- `normalize_entry_id()`

#### `health.py`
This module handles:
- root browser message
- `/health`
- `/ready`
- logs export

Main functions:
- `root()`
- `health()`
- `ready()`
- `logs_export_csv()`

The `ready()` endpoint checks whether the app has loaded the settings, Chroma collection, embedder, and HTML file correctly.

---

## 5. Service layer

The service layer is where orchestration happens.

### `backend/app/services/chat_service.py`

This module connects retrieval, model completion, and PDF mapping.

#### Main functions

##### `run_retrieve()`
A thin wrapper around the retrieval layer.

##### `run_ask()`
This is the main orchestration function for one question-answer cycle.

It typically:
- retrieves relevant chunks
- passes them to the model
- parses the response
- maps chunks to PDF pages/blocks
- returns a structure containing answer blocks, sources, operator detail, and timings

### Why this layer exists

Without a service layer, route handlers would become too large. This module keeps the “what to do” logic separate from the HTTP layer.

---

### `backend/app/services/conversation.py`

This module normalizes and serializes conversation history.

#### Main functions

##### `normalize_conversation(messages)`
Ensures messages follow the expected shape.

It:
- keeps only valid `user` and `assistant` entries
- normalizes user content to text
- preserves assistant blocks and operator detail where present

##### `append_turn(...)`
Adds a new user/assistant exchange to a conversation payload.

##### `conversation_to_csv(...)`
Exports conversation history to CSV.

##### `conversation_from_csv(...)`
Parses CSV conversation data back into message structure.

##### `conversation_to_json_bytes(...)`
Serializes conversation to JSON bytes for download/export.

### Why this matters

Conversation formatting is easy to get wrong if it is handled in the API layer directly. Keeping it here makes testing and reuse much simpler.

---

## 6. RAG layer

This is the heart of the chatbot.

### `backend/app/rag/indexing.py`

This module builds and loads the knowledge base.

#### Main functions

##### `load_embedder()`
Returns the embedding function used for indexing and querying.

##### `build_knowledge_base_core(settings, progress_callback=None)`
This is the core knowledge-base builder.

It:
- loads or initializes Chroma
- checks index schema version
- ensures the annotated book HTML is available
- parses the book HTML into chunks
- embeds and stores chunks in Chroma

##### `get_annotated_book_html(settings)`
Returns the annotated book HTML content.

##### `build_knowledge_base(settings)`
A cached wrapper that calls the core builder.

### Important implementation detail

The module includes an `INDEX_SCHEMA_VERSION` constant. That is useful because it allows the project to detect when metadata structure changes and the index should be rebuilt.

---

### `backend/app/rag/retrieve.py`

This module performs similarity retrieval.

#### Main function

##### `retrieve(query, collection, embedder, settings, top_k=None)`
This function:
- embeds the query
- performs vector search against the Chroma collection
- applies distance filtering
- returns a ranked list of relevant chunk dictionaries

### Returned data

The returned chunk dictionaries include metadata such as:
- document text
- section number
- section title
- heading id
- chunk id
- anchor id

This function is intentionally compact. It should stay focused on retrieval and not drift into response formatting or UI concerns.

---

### `backend/app/rag/book_document.py`

This module prepares the annotated book HTML used by the embedded viewer.

#### Main functions

##### `package_assets_dir()`
Returns the backend assets directory.

##### `inject_book_viewer_assets(...)`
Injects the book viewer CSS/JS and optional encyclopedia link styling.

##### `inline_local_images(...)`
Inlines local book images so the rendered HTML can be viewed correctly.

##### `resolve_book_html_path(settings)`
Resolves the current annotated book HTML file.

##### `build_annotated_book_document(settings, include_encyclopedia_links=False)`
Builds the HTML sent to the frontend book iframe.

### Why this matters

This module bridges document preprocessing and user-facing rendering. It is where the annotated book becomes viewable in the browser.

---

### `backend/app/rag/encyclopedia_document.py`

This module prepares the encyclopedia entry view.

#### Main functions

##### `prepared_encyclopedia_path(settings=None)`
Returns the source encyclopedia HTML path.

##### `annotated_book_path(settings=None)`
Returns the annotated book output HTML path.

##### `link_css_path()`
Returns the CSS file that styles the encyclopedia/book cross-links.

##### `normalize_entry_id(entry_id)`
Normalizes and validates entry identifiers.

##### `extract_entry_inner_html(...)`
Extracts the correct encyclopedia content region from the source document.

##### `build_encyclopedia_entry_document(...)`
Builds the HTML for a specific encyclopedia entry.

##### `build_encyclopedia_placeholder_document()`
Returns the placeholder document shown before an encyclopedia entry is selected.

### Why this module is important

This is directly related to the regression you observed. If the encyclopedia path or source selection changes, this module is one of the first places to inspect.

---

### `backend/app/rag/sources.py`

This module builds source metadata structures for the model output and UI.

It is a supporting module that helps turn retrieved chunks into a consistent list of source objects.

---

## 7. Language model layer

### `backend/app/llm/ask.py`

This module handles Groq completion with retrieval context.

#### Main function

##### `ask_groq(...)`
This is the main model-call function.

It typically:
- loads or uses the system prompt template
- prepares response language behavior
- formats retrieved context
- calls the Groq client
- normalizes the output into structured answer blocks
- creates fallback output if the model response is incomplete

### Helper behavior inside the module

It contains helper logic for:
- response language labels
- encyclopedia hint messages
- weak retrieval detection
- fallback answer text

### Why this matters

This module is the place to inspect if:
- the response format changes
- JSON parsing fails
- answer blocks are missing
- fallback text appears unexpectedly

---

### `backend/app/llm/parsing.py`

This is one of the largest backend modules and it exists for a reason: model output is messy.

#### Major functions

##### `parse_llm_json_blob(raw)`
Attempts to extract and parse JSON from model output even if the response contains prose, code fences, or multiple fragments.

##### `salvage_answer_blocks_from_near_json(...)`
Recovers structured answer data when the model output is close to JSON but not fully valid.

##### `fallback_plain_text_when_json_unparsed(...)`
Builds a fallback response when the JSON cannot be parsed.

##### `normalize_answer_blocks(...)`
Converts model output into a stable answer-block structure.

##### `message_when_no_answer_blocks(...)`
Generates a response when no structured blocks are available.

##### `operator_detail_no_blocks(...)`
Builds operator-facing detail for the no-blocks case.

### Why this matters

This file is the “messy text recovery” layer. It exists so that the app can still behave sensibly when the model output is imperfect.

---

### `backend/app/llm/prompts.py`

This module loads the system prompt template used by the model layer.

It keeps prompt text out of the orchestration logic, which is a good separation.

---

### `backend/app/llm/groq_client.py`

This module loads the Groq client from environment settings. It is used during application startup and by the model layer.

---

## 8. PDF layer

### `backend/app/pdf/index.py`

This module builds and queries a PDF page index.

#### Main functions

##### `load_pdf_index_uncached(pdf_path)`
Loads PDF blocks and page-level text without caching.

##### `load_pdf_index(pdf_path)`
Cached wrapper around the uncached loader.

##### `best_page_and_block(...)`
Finds the best match between a text chunk and a PDF block.

##### `map_chunks_to_pdf_core(...)`
Maps retrieved chunks to PDF pages and block metadata.

##### `map_chunks_to_pdf(...)`
Cached wrapper around the core mapper.

### Why it matters

This module helps connect retrieved text back to its source page in the PDF, which is useful for grounding and user navigation.

---

### `backend/app/pdf/text.py`

This module provides small text helpers for PDF search.

#### Main functions

- `make_pdf_search_query(text, max_words)`
- `norm_text(text)`
- `keyword_set(text, max_words)`

These helpers prepare text for search and matching.

---

### `backend/app/pdf/viewer.py`

This module supports PDF viewing in the browser.

#### Main functions

- `load_pdf_data_uri(pdf_path)`
- `render_pdf_viewer(pdf_data_uri, search_query="", page_number=None, height=760)`

This module turns a local PDF into a browser-friendly embedded viewer.

---

## 9. Database layer

### `backend/app/database/db.py`

This module stores chat logs in SQLite.

#### Main functions

- `init_db()`
- `log_interaction(message_id, chat_id, user_query, bot_response)`
- `update_feedback(message_id, feedback)`
- `get_all_logs()`
- `get_logs_csv_string()`

### Why this matters

This is the simplest persistence layer in the project, but it is still important because it supports:
- chat history tracking
- feedback recording
- CSV export of logs

### Note for maintainers

The module currently uses:

- `DB_PATH = Path.cwd() / "chatbot_logs.db"`

That is worth checking in deployment, because working-directory-based paths can be fragile if the server starts from a different location.

---

## 10. HTML sectioning utilities

### `backend/app/utils/html_sectioning.py`

This file is a compatibility facade.

It keeps the old import path alive while delegating to the more modular core package. That makes the refactor safer because existing imports do not break immediately.

### The core modules

The actual implementation lives in:

- `html_sectioning_core/helpers.py`
- `html_sectioning_core/parsing.py`
- `html_sectioning_core/chunking.py`
- `html_sectioning_core/annotation.py`
- `html_sectioning_core/numbering.py`
- `html_sectioning_core/models.py`
- `html_sectioning_core/legacy.py`
- `html_sectioning_core/constants.py`

### Main functions in the core

#### `helpers.py`
- `load_html_file()`
- `find_book_root()`
- `normalize_whitespace()` helpers
- section traversal helpers

#### `parsing.py`
- `parse_book_html()`

#### `chunking.py`
- `parse_html_to_paragraph_chunks()`
- `word_chunks()`
- `records_to_indexed_chunks()`

#### `annotation.py`
- `annotate_html_with_section_ids()`

#### `numbering.py`
- `annotate_html_with_numbering()`

### Why this refactor is strong

This is one of the best examples of real codebase improvement:
- parsing is separated from chunking
- chunking is separated from annotation
- annotation is separated from numbering
- legacy behavior is isolated instead of buried in one file

---

## 11. Backend request flow: what happens when a user asks a question

A simplified path is:

1. The frontend sends a question to `/ask`.
2. `backend/app/api/ask.py` receives the request.
3. `services/chat_service.py` orchestrates retrieval and model completion.
4. `rag/retrieve.py` finds relevant chunks.
5. `llm/ask.py` sends the prompt to Groq and parses the response.
6. `pdf/index.py` maps chunks to PDF locations if needed.
7. `services/conversation.py` appends the new turn.
8. The API returns the structured answer and source information.

That flow is the central behavior of the backend.

---

## 12. What new contributors should remember

If you are new to this codebase, the fastest way to understand the backend is:

1. Start with `backend/app/main.py`
2. Read `backend/app/config/settings.py`
3. Read `backend/app/api/ask.py`
4. Read `backend/app/services/chat_service.py`
5. Read `backend/app/rag/retrieve.py`
6. Read `backend/app/llm/ask.py`
7. Read `backend/app/rag/encyclopedia_document.py`
8. Read `backend/app/utils/html_sectioning.py`

That gives a good mental model of how the app starts, fetches context, answers, and renders sources.

---

## 13. Backend summary

The backend is now much more maintainable than the earlier monolithic structure because each major responsibility has a clear home.

The most important design ideas are:
- startup logic belongs in `main.py`
- request parsing belongs in `api/`
- orchestration belongs in `services/`
- retrieval belongs in `rag/`
- model parsing belongs in `llm/`
- PDF mapping belongs in `pdf/`
- configuration belongs in `config/`
- persistence belongs in `database/`
- HTML parsing/sectioning belongs in `utils/`

That separation is the main reason the refactor is meaningful.

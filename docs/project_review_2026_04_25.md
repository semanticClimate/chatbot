# Chatbot Project Review

**Date:** 2026-04-25 (system date of generation)
**Project:** `chatbot`

## Purpose and Main Workflows

This repository implements a climate-focused retrieval-augmented chatbot using Streamlit, local embeddings, and Chroma for vector search.

Primary workflow:

1. Parse HTML source content into section-aware records.
2. Chunk and embed section text.
3. Persist embeddings in a local Chroma collection.
4. On user query, retrieve nearest chunks and build grounded context.
5. Generate a response through Groq and present it in the Streamlit UI.

Key references:

- `README.md`
- `climate_streamlit/app.py`
- `climate_streamlit/html_sectioning.py`

## Architecture Summary

- `climate_streamlit/app.py`
  - Entry point for UI and runtime orchestration.
  - Handles cache setup, vector store initialization, retrieval, prompt assembly, and Groq calls.
- `climate_streamlit/html_sectioning.py`
  - Parsing utilities for nested section HTML.
  - Defines section/chunk data models and chunking pipeline.
- `tests/test_html_sectioning.py`
  - Parser and chunking tests for section extraction, numbering, overlaps, and integration behavior.
- `input/`
  - Source HTML assets, including sample and larger book files.
- `docs/HTML_SECTION_NESTING.md`
  - Structural guidance for expected HTML nesting and numbering.

## Test Status and Coverage Notes

- Current automated test suite is focused and passing (`pytest -q` reported all tests passing).
- Existing tests mainly cover parsing/chunking behavior in `html_sectioning.py`.
- Limited direct automated coverage for application-layer logic in `app.py`:
  - Retrieval threshold and filtering behavior.
  - Prompt construction and conversation-window logic.
  - Groq API failure handling and UI fallback paths.

## Risks and Technical Debt

1. **Static runtime configuration in code**
   - Paths and retrieval/model parameters are mostly fixed in `app.py`, requiring code edits for environment changes.
2. **Broad exception handling around generation**
   - Error handling in the LLM call path is generic, reducing diagnosability.
3. **`assert` for runtime file checks**
   - File existence checks in parser flow should prefer explicit exceptions for reliability in all runtimes.
4. **Potential retrieval quality drift**
   - Distance threshold and fallback behavior can admit weak context without visibility metrics.
5. **Repository hygiene**
   - Stored data artifacts and vector DB state increase repository weight and can complicate sharing/reproducibility policy.

## Recommended Next Priorities

1. Add unit tests for pure app logic in `app.py` (retrieval filter, prompt assembly, message windowing, API error mapping).
2. Replace runtime `assert` checks with explicit exceptions and user-facing error paths in `html_sectioning.py`.
3. Move key knobs (input file, top-k, threshold, model IDs) to configuration/environment values.
4. Add structured logging for retrieval quality and LLM/API failures.
5. Add or refine `.gitignore` policy for generated/vector data and large temporary assets.
6. Add coverage reporting (for example, `pytest-cov`) and establish a baseline target.

## Quick Assessment

The project has a clear and coherent retrieval pipeline with good parser-focused tests and useful domain structure. The highest-value improvements are in app-layer test coverage, runtime configurability, and operational observability.

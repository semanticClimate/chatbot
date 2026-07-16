## Session Summary - 2026-04-27

- Date source: `Mon Apr 27 10:57:55 BST 2026` (system `date` command).
- Scope: Read guideline-oriented docs in `../amilib` and `../pygetpapers`, then summarize for this session.

### Sources Reviewed

#### `../amilib`
- `README.md`
- `workflow/README.md`
- `amilib/workflow/README.md`

#### `../pygetpapers`
- `README.md`
- `GETTING_STARTED.md`
- `QUICK_REFERENCE.md`
- `docs/styleguide.md`

### Guideline Summary

#### amilib
- Developed in a test-driven style: tests are treated as functional guides and usage examples.
- Core workflow is CLI-first and organized around subcommands: `DICT`, `HTML`, `PDF`, `SEARCH`.
- Intended role is pipeline integration with `pygetpapers`, `docanalysis`, and related tools rather than a single standalone endpoint.
- Workflow docs emphasize a staged pipeline: retrieval -> conversion -> filtering/analysis -> annotation -> knowledge graph output.

#### pygetpapers
- Prefer climate-focused query examples in docs/demos.
- In examples, include full capability flags where relevant (XML/PDF/HTML/datatables) to demonstrate end-to-end behavior.
- Keep outputs out of repo root; use structured output paths (home directory target and/or `temp/` for disposable outputs).
- Use naming/path/import conventions consistently (underscore file names, explicit path patterns, absolute imports, no `sys.path` tricks).
- Always use and document verified system dates when dating docs or generated artifacts.
- Follow strict change discipline in the style guide: propose plan first, small steps, validation/testing, and avoid destructive commands without explicit approval.

### Notes

- `../pygetpapers/docs/styleguide.md` is the most explicit policy document among reviewed files.
- `../amilib` guidance is more architecture/workflow-oriented than rule-heavy.

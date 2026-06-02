# Climate encyclopedia sources (sibling `encyclopedia` repo)

This note summarizes meaningful **climate-oriented encyclopedia-style ground truth** in the sibling repository `../encyclopedia` (path: `encyclopedia/` next to `chatbot/`). **Semantic** here matches how that project uses the term: **structured entries** (terms, definitions/descriptions, often **Wikidata / Wikipedia URLs**, cross-links, optional figures) suitable for parsing, deduplication, and RAG.

---

## 1. Curated small climate encyclopedia (high signal, explicit semantics)

- **`Examples/simple_encyclopedia_example.html`** — Hand-authored-style demo with linked entries (e.g. climate change, greenhouse gas, methane, IPCC), **`wikidataID` attributes**, and internal `#` links between entries. Compact “textbook” semantic graph in HTML form.

---

## 2. Wikipedia-backed corpora (broad coverage, same entry model)

- **Root outputs:** `demo_encyclopedia.html`, `encyclopedia_output.html`, `my_encyclopedia.html` — Typical outputs from the wordlist pipeline; when built from climate wordlists they behave like medium-to-large climate-skewed encyclopedias in the same `AmiEncyclopedia` HTML format.
- **`Examples/example_wordlist.txt`** — Default climate-oriented seed list (e.g. climate change, IPCC, carbon cycle, ocean acidification).
- **`temp/climate_encyclopedia.html`** and **`temp/test/encyclopedia/GeneratedWithImages/climate_encyclopedia_with_images.html`** — Explicit climate test/demo HTML corpora (the images variant stresses figure / visual sections).

The aggregation script `scripts/count_climate_encyclopedia_entries.py` merges these HTML sources, deduplicates by **Wikidata / Wikipedia URL / term**, and can export **`temp/chatbot/climate_encyclopedia_entries.json`** for indexing (on the order of hundreds of unique entries; see `docs/CLIMATE_CHATBOT_DESIGN.md` in the encyclopedia repo).

---

## 3. Fixture cache encyclopedias (scaled regression corpora)

Under **`test/encyclopedia/fixtures/cache/`**, three cached builds matter for **semantic scale** and tests:

| Cache file (HTML) | Metadata title (from JSON) | Role |
|-------------------|-----------------------------|------|
| `encyclopedia_cb7e5726e56b3f32.html` | **Small Test Encyclopedia** (10 terms) | Tiny mix: climate + general science |
| `encyclopedia_11b5fdfc2f0b4253.html` | **Medium Test Encyclopedia** (59 terms) | Climate core + broader STEM / infra terms |
| `encyclopedia_1b74ac04211f6269.html` | **Large Test Encyclopedia** (478 entries) | Dominated by **climate and Earth-system** vocabulary (long climate-heavy wordlist in JSON) |

These are the main **volume** sources for consistent, repeatable evaluation of parsing, dedup, and chatbot behavior.

---

## 4. Knowledge-graph-oriented example (structure, not only prose)

- **`Examples/knowledge_graph_encyclopedia.html`** — Example encyclopedia used alongside the **knowledge graph** tooling (Wikidata-style relationships, exports). Semantics are still encyclopedia entries, but the emphasis is on **graph-backed** structure for analysis or enrichment.

---

## 5. Dictionary / IPCC branch (climate science text, different packaging)

- **`Dictionary/`** (per encyclopedia root `README.md`) — Holds **IPCC WG1** chapter material with extracted keywords and text. Not the same AMI HTML encyclopedia format, but strong **climate scientific ground truth** if “encyclopedia” is extended to structured reference corpora.

---

## 6. semanticClimate context (project identity, not a single file)

The encyclopedia root README points to **semanticClimate** assets (e.g. demo book, blog on the climate encyclopedia). That frames the **intended domain** (climate communication + open tooling); the files you wire into ground truth are still the HTML/JSON paths above.

---

## Practical takeaway for ground truth

The stack that best matches **semantic climate encyclopedias** in the sibling repo:

1. **`simple_encyclopedia_example.html`** — clean reference semantics  
2. **Fixture large / medium / small cache HTML** — scale + regression  
3. **Climate-named `temp/` HTML** and **root demo/output encyclopedias** when generated from climate wordlists  
4. Optional **`knowledge_graph_encyclopedia.html`** — graph semantics  

For a single merged index inside the encyclopedia project, run:

```bash
python scripts/count_climate_encyclopedia_entries.py --export
```

to produce deduplicated JSON under `temp/chatbot/` (gitignored there) for downstream indexing.

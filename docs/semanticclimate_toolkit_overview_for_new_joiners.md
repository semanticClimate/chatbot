# semanticClimate toolkit overview (for new joiners)

**Date:** 2026-07-24 (system date of generation)  
**Audience:** people with computing / climate data-science background  
**Scope:** public motivation + core repos (overview only; no implementation in this note)  
**Also for:** Renu / public onboarding pages

---

## Where to start (motivation first)

1. **Public events / learning path** — [OKFN AI Learning Labs](https://blog.okfn.org/category/okfn-projects/ai-learning-labs/)  
   Best on-ramp: intern presentations explain *why* the work exists and how pipelines fit together (~5 short talks; LatAm decks from Aleena Harold Peter / Vrinda Sharma as shared in community chat).

2. **Architecture mindset**  
   Work is **modular nodes** in a pipeline: each node has **inputs → function → outputs → parameters**, preferably **stateless**, with I/O as **Unicode files** on public store (easy to test; trade-off is more read/write). Typical node layout: **`examples/` · `tests/` · `scripts/`**.

3. Then pick a **node** that matches your interest (search → transform → knowledge → chat).

---

## Pipeline map (mental model)

```text
Open literature / IPCC-like sources
        │
        ▼
  pygetpapers / semantic_corpus     ← find & download / manage corpora
        │
        ▼
  amilib (+ HTML/IPCC tooling)      ← normalize, analyze, annotate text/HTML
        │
   ┌────┴────┐
   ▼         ▼
encyclopedia   (optional) pyamiimage / openDiagram
   │              ← terms/KG-ish views     ← figures/diagrams (not core intern path)
   ▼
chatbot / ClimateInsight            ← grounded Q&A over a corpus
```

---

## Core toolkit (with maturity)

Maturity here is **practical**: tests/docs/examples, how active pushes look, and whether newcomers can run something useful soon. Not a formal release audit.

| Repo | Role in the toolkit | Maturity (indicative) | Notes for joiners |
|------|---------------------|------------------------|-------------------|
| **[petermr/pygetpapers](https://github.com/petermr/pygetpapers)** | Query open repositories (e.g. Europe PMC) and download papers | **Mature / widely used** | Oldest “product” feel; versioned (e.g. `1.2.5a*`), strong `examples/` + `tests/` + docs + CI. Good first technical clone if you care about **literature acquisition**. |
| **[petermr/amilib](https://github.com/petermr/amilib)** | Library for download/analysis of OA + authoritative climate docs (IPCC/UNFCCC-oriented utilities, HTML/NLP helpers) | **Mature library, still evolving** | Explicitly **TDD-heavy**; large `test/` + `docs/` + `scripts/`. Hub for “text/HTML node” work. Entry often via tests/CLI. |
| **[semanticClimate/semantic_corpus](https://github.com/semanticClimate/semantic_corpus)** | Create/manage personal scientific corpora (search/download/organize; BAGIT option) | **Active early product (alpha)** | Version `0.1.0a1`; clear README features; tests/examples/docs present; recent pushes. Good if you like **corpus ops / research data management**. |
| **[semanticClimate/encyclopedia](https://github.com/semanticClimate/encyclopedia)** | Keyword / encyclopedia extraction & browsing over scientific/climate material | **Active mid-stack** | Substantial examples/docs/tests; browser UX. Bridges **corpus → browsable knowledge**. |
| **[semanticClimate/chatbot](https://github.com/semanticClimate/chatbot)** | Grounded climate chatbot (RAG over book/HTML; FastAPI + browser UI; OKFN/learning-lab line) | **Active product, early versioned** | `0.1.0a1` in `pyproject.toml`; recent commits; tests + installation docs; multilingual web client path. Natural home if you want **RAG / LLM + climate education**. |
| **[semanticClimate/ClimateInsight](https://github.com/semanticClimate/ClimateInsight)** | Aleena’s IPCC-oriented RAG chatbot (Ollama-centred setup in README) | **Young / demo–product** | Created mid-2026; fewer tests than `chatbot`; useful sibling to compare **local-LLM vs API** styles. |
| **[petermr/pyamiimage](https://github.com/petermr/pyamiimage)** | Extract semantics from scientific **images/diagrams** (e.g. pathways) | **Specialist / research-grade** | Versioned (`0.0.x`), tests/examples exist; needs Tesseract etc. **Not** current intern default, but open for image/ML interest. |
| **[petermr/openDiagram](https://github.com/petermr/openDiagram)** | Semantic recovery from diagrams (phylogenies, chem, forest plots, …) | **Research / largely dormant upstream** | Last substantive push old (~2021); ambitious scope; pair with `pyamiimage` if exploring diagram AI—not day-1 onboarding. |

---

## Related semanticClimate surface (not the “core eight”, but useful)

| Area | Examples | Maturity |
|------|----------|----------|
| Community / onboarding site | [semanticClimate/p](https://github.com/semanticClimate/p) (website), `presentations`, `internship_sC` | Content/community; recently touched |
| Literature-review product narrative | [assisted-literature-review](https://github.com/semanticClimate/assisted-literature-review) | Mid; visible ALR story |
| IPCC HTML / styles / corpus dumps | `ipcc`, `ipcc_corpus`, `ipcc-styles`, older conversion repos | Mixed: valuable **data/assets**, tooling uneven |
| Workshops / demos | `sC-tools-demo`, hackathon repos, `rag-test` | Ephemeral or teaching |

---

## Suggested paths by background

| If you… | Start with | Then |
|---------|------------|------|
| Want the **story + demos** | OKFN Learning Labs posts + short talks | Clone `chatbot` *or* `ClimateInsight` and run README |
| Like **search / APIs / download pipelines** | `pygetpapers` | `semantic_corpus` |
| Like **NLP / HTML / structured docs** | `amilib` tests as tutorials | `encyclopedia` |
| Like **RAG / eval / UX** | `chatbot` | Compare `ClimateInsight` |
| Like **vision / figures** | `pyamiimage` README | Skim `openDiagram` for problem framing |

---

## Practical expectations for new members

- Prefer **public Unicode artifacts** and tests over opaque binaries.  
- Many repos are **alpha** (`0.x` / `aN`) even when heavily used—version discipline is intentional.  
- “Mature” here often means **test-driven libraries + examples**, not polished SaaS.  
- Intern/OKFN work sits on top of older **petermr/** foundations (`pygetpapers`, `amilib`) plus newer **semanticClimate/** products (`semantic_corpus`, `encyclopedia`, `chatbot`, `ClimateInsight`).

---

## One-line takeaway

**semanticClimate is a modular open pipeline from open literature → cleaned text/HTML → knowledge views → grounded climate chatbots; start at OKFN Learning Labs for motivation, then `pygetpapers`/`amilib` for foundations or `chatbot`/`ClimateInsight` for RAG applications—image/diagram tools exist but are optional specialist tracks.**

# Session summary — Makespace Drive pilot & training analysis

**Date:** 2026-07-22 (system date of generation)  
**Repo:** chatbot  
**Theme:** Pilot analysis of Cambridge Makespace-style equipment documentation from Google Drive; scripts, controlled vocabulary, manager authorisation pack

---

## 1. Context and goal

The team has equipment documentation on Google Drive. The goal of this session was to:

1. Obtain a **pilot sample** (first ~10 folders) locally  
2. Analyse **folder structure** and **Training Information** content  
3. Derive a **controlled vocabulary** and **common subtopics**  
4. Package results for a **team manager** decision on analysing the **full** Drive library  

Drive URL (sign-in required; not readable by unauthenticated automation):  
https://drive.google.com/drive/folders/1-LuFZ6D-TNhYY9NWUGkLzlWPJzraUEq8

---

## 2. What we did

### 2.1 Access and download

- Confirmed the agent **cannot** read private Google Drive without auth (no Drive MCP / `rclone` / `gcloud` in this environment).  
- User downloaded **10** folder zips manually into `makespace/`.  
- Unpacked each zip into a directory named after the zip (minus `.zip`).  
- One Fume Extractor PDF needed sanitised extraction (illegal byte sequence / en-dash in filename).

### 2.2 Folder analysis script

Created and ran:

- `scripts/analyze_makespace_folders.py`

Parses Drive export names `{Equipment}-{YYYYMMDD}T{HHMMSS}Z-{part}-{seq}`, checks nested layout, counts manuals vs training files, and suggests **safe slugs** using only `[a-zA-Z0-9_]` (e.g. `Brymen_Multimeter`).

```bash
python3 scripts/analyze_makespace_folders.py
python3 scripts/analyze_makespace_folders.py --json
```

### 2.3 Training analysis script

**Incident:** Team ran `python3 scripts/analyze_makespace_training.py` before the file existed → `[Errno 2] No such file or directory`. Cause: script was **planned** in chat but not yet written; only `analyze_makespace_folders.py` existed.

**Fix:** Implemented `scripts/analyze_makespace_training.py`, which:

- Walks `Training Information/` under each equipment tree  
- Skips Office lock files (`~$…`)  
- Extracts paragraph text from `.pptx` (stdlib zip + XML)  
- Builds a controlled vocabulary of heading-like labels  
- Summarises file types  
- Optionally writes reports under `temp/makespace/`

```bash
python3 scripts/analyze_makespace_training.py
python3 scripts/analyze_makespace_training.py --json
```

### 2.4 Subtopics and taxonomy

From the pilot content, proposed common subtopic families:

| Code | Family |
|------|--------|
| `safety` | DO/DON’T, GREEN risk band, electrical, fault reporting |
| `pre_use` | Checks before first use, preparation |
| `operation` | Operating musts, handling |
| `beginner` | Learning objectives, scope, overview, PPE |
| `procedure` | Soldering / desoldering / rework steps |
| `materials_and_settings` | Flux, solder, tips, temperature, nozzles |
| `after_use` | Cleanup, shutdown / charge rules |

**Pattern:** Most kits have a **1-slide safety** deck; rich beginner/procedure content is mainly **Hakko Soldering Iron** and **Hot Air Rework Station**.

### 2.5 Manager package

Created durable docs for authorisation:

| Path | Role |
|------|------|
| `docs/makespace/README.md` | Index of the package |
| `docs/makespace/manager_brief_pilot_training_analysis.md` | **Manager brief** (decision checkboxes) |
| `docs/makespace/appendix_training_analysis_report.md` | Detailed tables |
| `docs/makespace/appendix_training_controlled_vocab.json` | Vocab snapshot |

---

## 3. Pilot findings (numbers)

| Metric | Value |
|--------|------:|
| Equipment folders | 10 |
| Training files seen | 12 |
| Training files analysed | 11 |
| Training file type | `.pptx` only |
| Controlled vocabulary terms | 58 |
| Empty training (no PPTX) | `Fume_Extractor` |

---

## 4. Artifacts created this session

### Recommended to commit (docs + scripts)

```text
scripts/analyze_makespace_folders.py
scripts/analyze_makespace_training.py
docs/makespace/README.md
docs/makespace/manager_brief_pilot_training_analysis.md
docs/makespace/appendix_training_analysis_report.md
docs/makespace/appendix_training_controlled_vocab.json
docs/summary/2026-07-22-makespace-pilot-training-analysis.md   # this file
```

### Usually do **not** commit (large / local / regenerable)

```text
makespace/*.zip
makespace/*/          # unpacked binaries (PPTX/PDF), large
temp/makespace/       # regenerable via --json (gitignored via temp/)
```

If the team wants a small fixture later, add a minimal sample under `test/` rather than the full Drive dump.

---

## 5. How to reproduce

```bash
cd /Users/pm286/workspace/chatbot
# assumes makespace/ already populated with unpacked folders
python3 scripts/analyze_makespace_folders.py --json
python3 scripts/analyze_makespace_training.py --json
```

Outputs: `temp/makespace/folder_analysis.json`, `training_*.json`, `training_analysis_report.md`.

---

## 6. Open decisions / next steps

- [ ] Manager authorises full Drive analysis (see manager brief §8)  
- [ ] Agree access method (link sharing, service account, or bulk export)  
- [ ] SME curation of the 58-term vocab (official vs incidental)  
- [ ] Optional Phase 3: parse **Manuals & Instructions** PDFs  
- [ ] Optional: rename local folders to safe slugs for cleaner paths  

---

## 7. Related earlier work (same broader project)

Earlier in the wider chatbot effort (separate from Makespace): IPCC SYR corpus sizing, `pyproject.toml` at repo root, multi-corpus config discussion, frontend naming. Those are not the focus of this Makespace pilot report.

---

## 8. One-line takeaway

Pilot of 10 Drive equipment folders shows **shared safety PPTX patterns** and **deep training only for soldering/rework**; scripts and a **manager authorisation brief** are ready — full Drive analysis awaits manager approval.

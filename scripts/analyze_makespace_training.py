#!/usr/bin/env python3
"""Analyze Training Information PPTX under makespace/ equipment folders.

Created: 2026-07-22 (system date of generation)

Walks each equipment tree, inventories Training Information files, extracts
paragraph text from .pptx (stdlib zip + XML), builds a controlled vocabulary
of heading-like labels, and summarizes file types.

Outputs under temp/makespace/ only (never the repo root).
Filenames use [a-zA-Z0-9_] (plus .json / .md extensions).
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

from analyze_makespace_folders import (
    DRIVE_DIR_RE,
    repo_root,
    system_date_ymd,
    to_safe_slug,
)

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}

LOCK_PREFIX = "~$"
KNOWN_HEADINGS = {
    "DO": "DO",
    "DO NOT": "DO_NOT",
    "DON'T": "DO_NOT",
    "DONT": "DO_NOT",
    "CHECKS BEFORE FIRST USE": "CHECKS_BEFORE_FIRST_USE",
    "WHEN OPERATING THIS EQUIPMENT YOU MUST": "WHEN_OPERATING_YOU_MUST",
    "IF IN DOUBT": "IF_IN_DOUBT",
}


@dataclass
class TrainingFile:
    equipment: str
    safe_slug: str
    relative_path: str
    extension: str
    size_bytes: int
    genre: str
    excluded: bool
    exclude_reason: str
    slide_count: int = 0
    paragraphs: list[list[str]] = field(default_factory=list)


def classify_genre(filename: str) -> str:
    lower = filename.lower()
    if "safety" in lower:
        return "safety"
    if "online" in lower and "training" in lower:
        return "online_training"
    if lower.endswith(".pptx"):
        return "training"
    return "other"


def find_training_dirs(makespace: Path) -> list[tuple[str, str, Path]]:
    """Return (equipment, safe_slug, training_dir) for each top-level folder."""
    results = []
    for top in sorted(p for p in makespace.iterdir() if p.is_dir()):
        match = DRIVE_DIR_RE.match(top.name)
        equipment = match.group("equipment") if match else top.name
        safe_slug = to_safe_slug(equipment)
        nested = top / equipment
        training = nested / "Training Information"
        if not training.is_dir():
            # fallback search
            found = list(top.rglob("Training Information"))
            training = found[0] if found else training
        results.append((equipment, safe_slug, training))
    return results


def extract_pptx_paragraphs(pptx: Path) -> list[list[str]]:
    """One list of paragraph strings per slide."""
    slides: list[list[str]] = []
    with zipfile.ZipFile(pptx) as zf:
        names = [
            n for n in zf.namelist()
            if re.match(r"ppt/slides/slide\d+\.xml$", n)
        ]
        names.sort(key=lambda s: int(re.search(r"slide(\d+)", s).group(1)))
        for name in names:
            root = ET.fromstring(zf.read(name))
            paras: list[str] = []
            for p_el in root.findall(".//a:p", NS):
                runs = [t.text for t in p_el.findall(".//a:t", NS) if t.text]
                text = "".join(runs).strip()
                if text:
                    paras.append(text)
            slides.append(paras)
    return slides


def is_heading_candidate(text: str) -> bool:
    t = text.strip()
    if not t or len(t) > 80:
        return False
    upper = t.upper()
    if upper in KNOWN_HEADINGS:
        return True
    if upper.startswith("GREEN EQUIPMENT"):
        return True
    # Short Title Case / ALL CAPS labels without ending punctuation
    if t.endswith((".", "!", "?")):
        return False
    words = t.split()
    if len(words) > 12:
        return False
    if t.isupper() and len(words) <= 8:
        return True
    if t == t.title() and len(words) <= 10 and not t[0].isdigit():
        return True
    return False


def vocab_id_for(text: str) -> str:
    upper = text.strip().upper()
    if upper in KNOWN_HEADINGS:
        return KNOWN_HEADINGS[upper]
    if upper.startswith("GREEN EQUIPMENT"):
        return "GREEN_EQUIPMENT"
    return to_safe_slug(text.strip())


def inventory_and_extract(makespace: Path) -> list[TrainingFile]:
    rows: list[TrainingFile] = []
    for equipment, safe_slug, training in find_training_dirs(makespace):
        if not training.is_dir():
            continue
        for path in sorted(training.rglob("*")):
            if not path.is_file():
                continue
            name = path.name
            ext = path.suffix.lower() or "(none)"
            excluded = False
            reason = ""
            if name.startswith(LOCK_PREFIX):
                excluded = True
                reason = "office_lock_file"
            genre = classify_genre(name)
            slide_count = 0
            paragraphs: list[list[str]] = []
            if not excluded and ext == ".pptx":
                try:
                    paragraphs = extract_pptx_paragraphs(path)
                    slide_count = len(paragraphs)
                except (zipfile.BadZipFile, ET.ParseError, KeyError) as exc:
                    excluded = True
                    reason = f"pptx_parse_error:{type(exc).__name__}"
            rows.append(
                TrainingFile(
                    equipment=equipment,
                    safe_slug=safe_slug,
                    relative_path=str(path.relative_to(makespace)),
                    extension=ext,
                    size_bytes=path.stat().st_size,
                    genre=genre,
                    excluded=excluded,
                    exclude_reason=reason,
                    slide_count=slide_count,
                    paragraphs=paragraphs,
                )
            )
    return rows


def build_controlled_vocab(files: list[TrainingFile]) -> dict:
    """Map vocab id -> metadata with aliases and equipment coverage."""
    terms: dict[str, dict] = {}
    for tf in files:
        if tf.excluded:
            continue
        for slide_paras in tf.paragraphs:
            for para in slide_paras:
                if not is_heading_candidate(para):
                    continue
                vid = vocab_id_for(para)
                if vid not in terms:
                    terms[vid] = {
                        "id": vid,
                        "label": para.strip(),
                        "kind": "heading",
                        "aliases": [],
                        "seen_in": [],
                        "raw_forms": [],
                    }
                entry = terms[vid]
                if para.strip() not in entry["raw_forms"]:
                    entry["raw_forms"].append(para.strip())
                if para.strip() != entry["label"] and para.strip() not in entry["aliases"]:
                    entry["aliases"].append(para.strip())
                if tf.safe_slug not in entry["seen_in"]:
                    entry["seen_in"].append(tf.safe_slug)
    # sort for stable output
    for entry in terms.values():
        entry["seen_in"].sort()
        entry["aliases"].sort()
        entry["raw_forms"].sort()
    return dict(sorted(terms.items()))


def filetype_summary(files: list[TrainingFile]) -> dict:
    all_ext = Counter(f.extension for f in files)
    analyzed_ext = Counter(f.extension for f in files if not f.excluded)
    excluded = [asdict(f) for f in files if f.excluded]
    empty_training = []
    # equipment with training dir but zero non-excluded files
    by_slug: dict[str, list[TrainingFile]] = defaultdict(list)
    for f in files:
        by_slug[f.safe_slug].append(f)
    for slug, group in by_slug.items():
        if not any(not g.excluded for g in group):
            empty_training.append(slug)
    return {
        "extension_counts_all": dict(all_ext),
        "extension_counts_analyzed": dict(analyzed_ext),
        "excluded_files": [
            {
                "relative_path": e["relative_path"],
                "reason": e["exclude_reason"],
            }
            for e in excluded
        ],
        "equipment_with_no_analyzed_training_files": sorted(empty_training),
        "total_files_seen": len(files),
        "total_analyzed": sum(1 for f in files if not f.excluded),
    }


def write_report(
    files: list[TrainingFile],
    vocab: dict,
    ftypes: dict,
    out_dir: Path,
    generated: str,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    inventory_path = Path(out_dir, "training_inventory.json")
    vocab_path = Path(out_dir, "training_controlled_vocab.json")
    report_path = Path(out_dir, "training_analysis_report.md")

    inventory = {
        "generated": generated,
        "date_source": "system date of generation",
        "files": [
            {
                "equipment": f.equipment,
                "safe_slug": f.safe_slug,
                "relative_path": f.relative_path,
                "extension": f.extension,
                "size_bytes": f.size_bytes,
                "genre": f.genre,
                "excluded": f.excluded,
                "exclude_reason": f.exclude_reason,
                "slide_count": f.slide_count,
                "paragraph_count": sum(len(s) for s in f.paragraphs),
            }
            for f in files
        ],
        "file_types": ftypes,
    }
    # Full paragraph dump optional companion
    extracts_path = Path(out_dir, "training_pptx_extracts.json")
    extracts = {
        "generated": generated,
        "files": [
            {
                "safe_slug": f.safe_slug,
                "relative_path": f.relative_path,
                "slides": f.paragraphs,
            }
            for f in files
            if not f.excluded and f.extension == ".pptx"
        ],
    }

    inventory_path.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    vocab_path.write_text(
        json.dumps(
            {
                "generated": generated,
                "date_source": "system date of generation",
                "term_count": len(vocab),
                "terms": vocab,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    extracts_path.write_text(json.dumps(extracts, indent=2) + "\n", encoding="utf-8")

    lines = [
        f"# Makespace Training Information analysis",
        f"",
        f"Generated: **{generated}** (system date of generation)",
        f"",
        f"## File types",
        f"",
        f"- Files seen: **{ftypes['total_files_seen']}**",
        f"- Analyzed (non-excluded): **{ftypes['total_analyzed']}**",
        f"- Extensions (all): `{ftypes['extension_counts_all']}`",
        f"- Extensions (analyzed): `{ftypes['extension_counts_analyzed']}`",
        f"",
    ]
    if ftypes["excluded_files"]:
        lines.append("### Excluded")
        lines.append("")
        for ex in ftypes["excluded_files"]:
            lines.append(f"- `{ex['relative_path']}` — {ex['reason']}")
        lines.append("")
    if ftypes["equipment_with_no_analyzed_training_files"]:
        lines.append("### Equipment with no analyzed training files")
        lines.append("")
        for slug in ftypes["equipment_with_no_analyzed_training_files"]:
            lines.append(f"- `{slug}`")
        lines.append("")

    lines.extend(
        [
            f"## Per-file summary",
            f"",
            f"| safe_slug | genre | slides | paras | file |",
            f"|-----------|-------|--------|-------|------|",
        ]
    )
    for f in files:
        if f.excluded:
            continue
        paras = sum(len(s) for s in f.paragraphs)
        short = Path(f.relative_path).name
        lines.append(
            f"| {f.safe_slug} | {f.genre} | {f.slide_count} | {paras} | `{short}` |"
        )

    lines.extend(
        [
            f"",
            f"## Controlled vocabulary ({len(vocab)} terms)",
            f"",
            f"| id | label | seen_in_count |",
            f"|----|-------|---------------|",
        ]
    )
    for vid, entry in vocab.items():
        lines.append(
            f"| `{vid}` | {entry['label']} | {len(entry['seen_in'])} |"
        )
    lines.append("")
    lines.append("Full machine-readable outputs:")
    lines.append("")
    lines.append(f"- `{inventory_path.name}`")
    lines.append(f"- `{vocab_path.name}`")
    lines.append(f"- `{extracts_path.name}`")
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote: {inventory_path}")
    print(f"wrote: {vocab_path}")
    print(f"wrote: {extracts_path}")
    print(f"wrote: {report_path}")


def print_console_summary(
    files: list[TrainingFile],
    vocab: dict,
    ftypes: dict,
    generated: str,
) -> None:
    print(f"# training analysis  ({generated}, system date of generation)")
    print(f"files seen: {ftypes['total_files_seen']}  analyzed: {ftypes['total_analyzed']}")
    print(f"extensions: {ftypes['extension_counts_analyzed']}")
    print(f"vocab terms: {len(vocab)}")
    print()
    for vid, entry in list(vocab.items())[:20]:
        print(f"  {vid:<40}  n={len(entry['seen_in']):2d}  {entry['label']!r}")
    if len(vocab) > 20:
        print(f"  ... +{len(vocab) - 20} more (see training_controlled_vocab.json)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze Training Information PPTX under makespace/."
    )
    parser.add_argument(
        "--root",
        type=str,
        default="",
        help="Path to makespace directory (default: <repo>/makespace)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Write inventory, vocab, extracts, and markdown report under temp/makespace/",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    makespace = Path(args.root).resolve() if args.root else Path(repo_root(), "makespace")
    assert makespace.is_dir(), f"makespace root not found: {makespace}"
    generated = system_date_ymd()

    files = inventory_and_extract(makespace)
    vocab = build_controlled_vocab(files)
    ftypes = filetype_summary(files)
    print_console_summary(files, vocab, ftypes, generated)

    # Always write report artifacts when --json; also write by default a light touch
    out_dir = Path(repo_root(), "temp", "makespace")
    if args.json:
        write_report(files, vocab, ftypes, out_dir, generated)
    else:
        print()
        print("Tip: re-run with --json to write temp/makespace/training_*.json and .md")


if __name__ == "__main__":
    main()

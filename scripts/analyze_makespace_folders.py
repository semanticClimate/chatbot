#!/usr/bin/env python3
"""Analyze top-level folder names under makespace/.

Created: 2026-07-22 (system date of generation)

Parses Google Drive export directory names of the form:
  {Equipment Name}-{YYYYMMDD}T{HHMMSS}Z-{part}-{seq}

Reports equipment label, export stamp, nested layout checks, and a
safe slug using only [a-zA-Z0-9_] (no spaces, hyphens, ampersands, etc.).

Output (optional JSON) goes under temp/makespace/ — never the repo root.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

# Drive zip folder: name-YYYYMMDDThhmmssZ-part-seq
DRIVE_DIR_RE = re.compile(
    r"^(?P<equipment>.+)-(?P<stamp>\d{8}T\d{6}Z)-(?P<part>\d+)-(?P<seq>\d+)$"
)
SAFE_CHARS_RE = re.compile(r"^[a-zA-Z0-9_]+$")
UNSAFE_RUN_RE = re.compile(r"[^a-zA-Z0-9_]+")


@dataclass(frozen=True)
class FolderRow:
    folder_name: str
    equipment: str
    safe_slug: str
    export_stamp: str
    part: str
    seq: str
    parse_ok: bool
    nested_equipment_ok: bool
    manuals_count: int
    training_count: int
    notes: str


def system_date_ymd() -> str:
    """Return YYYY-MM-DD from the system clock (style: verify date via date)."""
    out = subprocess.check_output(["date", "+%Y-%m-%d"], text=True)
    return out.strip()


def to_safe_slug(label: str) -> str:
    """Map a human label to [a-zA-Z0-9_] only (underscores for separators)."""
    slug = UNSAFE_RUN_RE.sub("_", label.strip())
    slug = re.sub(r"_+", "_", slug).strip("_")
    if not slug:
        slug = "unnamed"
    assert SAFE_CHARS_RE.match(slug), f"slug not safe: {slug!r}"
    return slug


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def count_files(directory: Path) -> int:
    if not directory.is_dir():
        return 0
    return sum(1 for p in directory.rglob("*") if p.is_file())


def analyze_folder(path: Path) -> FolderRow:
    name = path.name
    match = DRIVE_DIR_RE.match(name)
    notes: list[str] = []

    if match:
        equipment = match.group("equipment")
        stamp = match.group("stamp")
        part = match.group("part")
        seq = match.group("seq")
        parse_ok = True
    else:
        equipment = name
        stamp = ""
        part = ""
        seq = ""
        parse_ok = False
        notes.append("name_did_not_match_drive_export_pattern")

    safe_slug = to_safe_slug(equipment)

    nested = path / equipment
    nested_ok = nested.is_dir()
    if not nested_ok:
        # Fall back: single child directory
        children = [p for p in path.iterdir() if p.is_dir()]
        if len(children) == 1:
            nested = children[0]
            nested_ok = nested.name == equipment
            if not nested_ok:
                notes.append(f"nested_dir_is_{nested.name!r}_expected_{equipment!r}")
        else:
            notes.append("missing_nested_equipment_directory")

    manuals = nested / "Manuals & Instructions"
    training = nested / "Training Information"
    manuals_count = count_files(manuals)
    training_count = count_files(training)
    if manuals_count == 0:
        notes.append("no_manual_files")
    if training_count == 0:
        notes.append("no_training_files")

    return FolderRow(
        folder_name=name,
        equipment=equipment,
        safe_slug=safe_slug,
        export_stamp=stamp,
        part=part,
        seq=seq,
        parse_ok=parse_ok,
        nested_equipment_ok=nested_ok,
        manuals_count=manuals_count,
        training_count=training_count,
        notes=";".join(notes),
    )


def collect_rows(root: Path) -> list[FolderRow]:
    assert root.is_dir(), f"makespace root not found: {root}"
    dirs = sorted(p for p in root.iterdir() if p.is_dir())
    return [analyze_folder(p) for p in dirs]


def print_table(rows: list[FolderRow], generated: str) -> None:
    print(f"# makespace folder analysis  ({generated}, system date of generation)")
    print(f"count: {len(rows)}")
    print()
    header = (
        f"{'safe_slug':<28}  {'stamp':<17}  {'nested':<6}  "
        f"{'man':>3}  {'trn':>3}  equipment"
    )
    print(header)
    print("-" * len(header))
    for row in rows:
        nested = "yes" if row.nested_equipment_ok else "NO"
        print(
            f"{row.safe_slug:<28}  {row.export_stamp or '-':<17}  {nested:<6}  "
            f"{row.manuals_count:>3}  {row.training_count:>3}  {row.equipment}"
        )
        if row.notes:
            print(f"  notes: {row.notes}")
    print()
    print("Suggested short folder names (safe [a-zA-Z0-9_] only):")
    for row in rows:
        print(f"  {row.safe_slug}")


def write_json(rows: list[FolderRow], out_path: Path, generated: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated": generated,
        "date_source": "system date of generation",
        "count": len(rows),
        "folders": [asdict(r) for r in rows],
    }
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote: {out_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze makespace/ top-level folder names from Drive exports."
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
        help="Also write temp/makespace/folder_analysis.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.root).resolve() if args.root else Path(repo_root(), "makespace")
    generated = system_date_ymd()
    rows = collect_rows(root)
    print_table(rows, generated)
    if args.json:
        out = Path(repo_root(), "temp", "makespace", "folder_analysis.json")
        write_json(rows, out, generated)


if __name__ == "__main__":
    main()

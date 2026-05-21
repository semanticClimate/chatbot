#!/usr/bin/env python3
"""Annotate the full CABook HTML using encyclopedia terms (config-driven)."""

from __future__ import annotations

import argparse
from pathlib import Path

from encyclopedia.cabook_annotate.pipeline import run_annotation_pipeline


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    default_config = Path(repo_root, "encyclopedia", "config", "annotate_cabook.toml")
    parser = argparse.ArgumentParser(
        description="Annotate CABook HTML with links to CA encyclopedia entries."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=default_config,
        help=f"Path to annotate_cabook.toml (default: {default_config})",
    )
    args = parser.parse_args()

    result = run_annotation_pipeline(args.config)
    print(f"Links inserted: {result['links_inserted']}")
    print(f"Encyclopedia entries: {result['entries']}")
    print(f"Surface forms: {result['surface_forms']}")
    print(f"Annotated book: {result['annotated_book_html']}")
    print(f"Prepared encyclopedia: {result['prepared_encyclopedia_html']}")
    print(f"Report: {result['report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

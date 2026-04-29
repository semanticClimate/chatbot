"""
Generate HTML with visible hierarchical section/paragraph numbering.

Usage:
  python climate_streamlit/numbered_html_cli.py
  python climate_streamlit/numbered_html_cli.py --input input/sample_ca_book.html --output temp/zoom_summaries/sample_ca_book_numbered.html
"""

from __future__ import annotations

import argparse
from pathlib import Path

from html_sectioning import annotate_html_with_numbering


def _default_input_path() -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    return Path(repo_root, "input", "sample_ca_book.html")


def _default_output_path(input_path: Path) -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    return Path(repo_root, "temp", "zoom_summaries", f"{input_path.stem}_numbered.html")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate numbered HTML for Climate Academy ingestion.")
    parser.add_argument(
        "--input",
        default=str(_default_input_path()),
        help="Source HTML file to annotate",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Output HTML path (defaults to temp/zoom_summaries/<input_stem>_numbered.html)",
    )
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()

    input_path = Path(args.input).expanduser()
    assert input_path.is_file(), f"Input HTML file not found: {input_path}"

    output_path = Path(args.output).expanduser() if args.output.strip() else _default_output_path(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    raw_html = input_path.read_text(encoding="utf-8", errors="replace")
    numbered_html = annotate_html_with_numbering(raw_html)
    output_path.write_text(numbered_html, encoding="utf-8")

    print(f"Input HTML: {input_path}")
    print(f"Numbered HTML written: {output_path}")


if __name__ == "__main__":
    main()

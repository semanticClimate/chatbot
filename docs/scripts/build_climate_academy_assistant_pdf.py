#!/usr/bin/env python3
"""Build docs/climate-academy-assistant-explained.pdf from the matching .md file."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from fpdf import FPDF

REPO_ROOT = Path(__file__).resolve().parents[2]
MD_PATH = REPO_ROOT / "docs" / "climate-academy-assistant-explained.md"
PDF_PATH = REPO_ROOT / "docs" / "climate-academy-assistant-explained.pdf"

MARGIN = 18
LINE = 5.5


class GuidePDF(FPDF):
    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, f"Climate Academy Assistant - page {self.page_no()}", align="C")

    def content_width(self, indent: float = 0) -> float:
        return self.w - 2 * MARGIN - indent


def write_block(
    pdf: GuidePDF,
    text: str,
    *,
    indent: float = 0,
    h: float = LINE,
    font: tuple[str, str, int] = ("Helvetica", "", 10),
    fill: bool = False,
) -> None:
    pdf.set_x(MARGIN + indent)
    pdf.set_font(*font)
    pdf.multi_cell(pdf.content_width(indent), h, strip_md_inline(text), fill=fill)


def strip_md_inline(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    return pdf_safe(text)


def pdf_safe(text: str) -> str:
    """Helvetica in fpdf2 is Latin-1 only; normalize common Unicode punctuation."""
    replacements = {
        "\u2014": " - ",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\u00a7": "Section ",
        "\u2082": "2",
        "\u2084": "4",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", "replace").decode("latin-1")


def is_table_row(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.endswith("|") and "|" in s[1:-1]


def parse_table_row(line: str) -> list[str]:
    parts = [p.strip() for p in line.strip().strip("|").split("|")]
    return parts


def is_separator_row(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-+:?", c.replace(" ", "")) for c in cells if c)


def build_pdf(md_text: str, out_path: Path) -> None:
    md_text = pdf_safe(md_text)
    pdf = GuidePDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_margins(MARGIN, MARGIN, MARGIN)

    in_code = False
    code_lines: list[str] = []
    i = 0
    lines = md_text.splitlines()

    while i < len(lines):
        line = lines[i]
        raw = line.rstrip()

        if raw.strip().startswith("```"):
            if in_code:
                pdf.set_fill_color(245, 245, 245)
                block = "\n".join(code_lines)
                write_block(
                    pdf,
                    block,
                    h=4.2,
                    font=("Courier", "", 8),
                    fill=True,
                )
                pdf.ln(2)
                code_lines = []
                in_code = False
            else:
                in_code = True
            i += 1
            continue

        if in_code:
            code_lines.append(raw)
            i += 1
            continue

        if not raw.strip():
            pdf.ln(3)
            i += 1
            continue

        if raw.startswith("# "):
            pdf.ln(2)
            pdf.set_text_color(20, 60, 100)
            write_block(pdf, raw[2:].strip(), h=9, font=("Helvetica", "B", 18))
            pdf.set_text_color(0, 0, 0)
            pdf.ln(2)
            i += 1
            continue

        if raw.startswith("## "):
            pdf.ln(4)
            pdf.set_text_color(30, 80, 120)
            write_block(pdf, raw[3:].strip(), h=7, font=("Helvetica", "B", 13))
            pdf.set_text_color(0, 0, 0)
            pdf.ln(1)
            i += 1
            continue

        if raw.startswith("### "):
            pdf.ln(2)
            write_block(pdf, raw[4:].strip(), h=6, font=("Helvetica", "B", 11))
            i += 1
            continue

        if raw.strip() == "---":
            pdf.ln(2)
            y = pdf.get_y()
            pdf.set_draw_color(200, 200, 200)
            pdf.line(MARGIN, y, pdf.w - MARGIN, y)
            pdf.ln(4)
            i += 1
            continue

        if is_table_row(raw):
            table_rows: list[list[str]] = []
            while i < len(lines) and is_table_row(lines[i]):
                cells = parse_table_row(lines[i])
                if not is_separator_row(cells):
                    table_rows.append(cells)
                i += 1
            if table_rows:
                ncols = len(table_rows[0])
                col_w = (pdf.w - 2 * MARGIN) / ncols
                pdf.set_font("Helvetica", "B", 9)
                pdf.set_x(MARGIN)
                for cell in table_rows[0]:
                    pdf.cell(col_w, 7, strip_md_inline(cell)[:60], border=1)
                pdf.ln()
                pdf.set_font("Helvetica", "", 9)
                for row in table_rows[1:]:
                    pdf.set_x(MARGIN)
                    for cell in row[:ncols]:
                        pdf.cell(col_w, 7, strip_md_inline(cell)[:60], border=1)
                    pdf.ln()
                pdf.set_x(MARGIN)
                pdf.ln(2)
            continue

        if raw.startswith("> "):
            pdf.set_text_color(50, 50, 50)
            write_block(pdf, raw[2:].strip(), font=("Helvetica", "I", 10))
            pdf.set_text_color(0, 0, 0)
            pdf.ln(1)
            i += 1
            continue

        if raw.startswith("- "):
            write_block(pdf, "• " + raw[2:].strip(), indent=4)
            i += 1
            continue

        if re.match(r"^\d+\.\s", raw):
            write_block(pdf, raw)
            i += 1
            continue

        if raw.startswith("*") and raw.endswith("*") and not raw.startswith("**"):
            pdf.set_text_color(80, 80, 80)
            write_block(pdf, raw.strip("* ").strip(), font=("Helvetica", "I", 9))
            pdf.set_text_color(0, 0, 0)
            i += 1
            continue

        write_block(pdf, raw)
        i += 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(out_path))


def main() -> int:
    if not MD_PATH.is_file():
        print(f"Missing source: {MD_PATH}", file=sys.stderr)
        return 1
    md_text = MD_PATH.read_text(encoding="utf-8")
    build_pdf(md_text, PDF_PATH)
    print(f"Wrote {PDF_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Tests for HTML outline parsing, annotation, and visible § labels."""

from pathlib import Path

from bs4 import BeautifulSoup

from backend.app.html_sectioning import (
    IndexedChunk,
    annotate_html_with_numbering,
    annotate_html_with_section_ids,
    parse_book_html,
    parse_html_path_to_chunks,
    parse_html_to_paragraph_chunks,
)
from backend.app.rag.book_document import (
    inject_book_viewer_assets,
    package_assets_dir,
)

PROTOTYPE = Path(Path(__file__).resolve().parents[1], "input", "sample_ca_book.html")

FORMAT_B_FIXTURE = """\
<!DOCTYPE html>
<html lang="en"><body>
<article id="climate-academy-book">
  <h1>Chapter Alpha</h1>
  <p>First chapter body with sufficient length for the flat-heading parser.</p>
  <h2>Topic Beta</h2>
  <p>Nested topic body with sufficient length for the flat-heading parser.</p>
</article>
</body></html>
"""

VISIBLE_SECTION_CSS_MARKER = '[data-section-number]::before'
VISIBLE_SECTION_CSS_CONTENT = '§ " attr(data-section-number)'


def test_parse_prototype_section_numbers_and_order():
    html = PROTOTYPE.read_text(encoding="utf-8")
    records = parse_book_html(html)
    numbers = [r.section_number for r in records]
    assert numbers == ["1", "1.1", "1.1.1", "1.1.2", "1.2", "2"], (
        f"Expected outline order, got {numbers!r}"
    )
    titles = [r.title for r in records]
    assert "Foundations of climate science" in titles[0]
    assert "The greenhouse effect" in titles[1]
    assert "Key greenhouse gases" in titles[2]


def test_parse_prototype_non_empty_bodies():
    html = PROTOTYPE.read_text(encoding="utf-8")
    records = parse_book_html(html)
    for r in records:
        assert r.body.strip(), f"Empty body for §{r.section_number} {r.title!r}"


def test_paragraph_chunks_contain_section_header():
    chunks = parse_html_to_paragraph_chunks(PROTOTYPE)
    assert chunks
    assert chunks[0].document.startswith("[§ ")
    assert "Foundations" in chunks[0].document or "greenhouse" in chunks[0].document.lower()


def test_parse_html_path_to_chunks_integration():
    chunks = parse_html_path_to_chunks(PROTOTYPE, chunk_size=30, chunk_overlap=5)
    assert len(chunks) >= len(parse_book_html(PROTOTYPE.read_text(encoding="utf-8")))
    assert isinstance(chunks[0], IndexedChunk)


def test_annotate_html_with_numbering_adds_section_and_paragraph_numbers():
    html = PROTOTYPE.read_text(encoding="utf-8")
    numbered_html = annotate_html_with_numbering(html)
    assert "data-section-number=\"1\"" in numbered_html
    assert "data-section-number=\"1.1\"" in numbered_html
    assert "data-paragraph-number=\"1.1.1\"" in numbered_html
    assert "id=\"s1\"" in numbered_html
    assert "id=\"s1-1_p1\"" in numbered_html
    assert "1 Foundations of climate science" in numbered_html


def test_annotate_html_with_numbering_uses_distinct_section_and_paragraph_id_syntax():
    html = PROTOTYPE.read_text(encoding="utf-8")
    numbered_html = annotate_html_with_numbering(html)
    assert "id=\"s1-1\"" in numbered_html
    assert "id=\"s1-1_p1\"" in numbered_html
    assert "id=\"s1-1\"" in numbered_html and "id=\"s1-1_p1\"" in numbered_html


def test_annotated_format_a_headings_carry_section_numbers():
    """Nested <section> books: § must be on the title heading, not only on <section>."""
    html = PROTOTYPE.read_text(encoding="utf-8")
    soup = BeautifulSoup(annotate_html_with_section_ids(html), "html.parser")
    for sec in soup.find_all("section", attrs={"data-section-number": True}):
        heading = sec.find(["h1", "h2", "h3", "h4", "h5", "h6"], recursive=False)
        if heading is None:
            heading = sec.find(["h1", "h2", "h3", "h4", "h5", "h6"])
        assert heading is not None, f"§{sec['data-section-number']} has no heading"
        assert heading.get("data-section-number") == sec["data-section-number"]


def test_annotated_format_b_headings_and_ca_section_wrappers():
    soup = BeautifulSoup(annotate_html_with_section_ids(FORMAT_B_FIXTURE), "html.parser")
    h1 = soup.find("h1", string=lambda t: t and "Chapter Alpha" in t)
    h2 = soup.find("h2", string=lambda t: t and "Topic Beta" in t)
    assert h1 is not None and h1.get("data-section-number") == "1"
    assert h2 is not None and h2.get("data-section-number") == "1.1"
    numbers = sorted(w["data-section-number"] for w in soup.find_all("div", class_="ca-section"))
    assert numbers == ["1", "1.1"]


def test_annotated_format_b_paragraphs_carry_paragraph_numbers():
    soup = BeautifulSoup(annotate_html_with_section_ids(FORMAT_B_FIXTURE), "html.parser")
    first_para = soup.find("p", attrs={"data-paragraph-number": "1.1"})
    second_para = soup.find("p", attrs={"data-paragraph-number": "1.1.1"})
    assert first_para is not None
    assert second_para is not None


def test_inject_book_viewer_assets_adds_visible_section_css():
    minimal = "<html><head></head><body><h2 data-section-number='1'>Title</h2></body></html>"
    out = inject_book_viewer_assets(minimal)
    assert VISIBLE_SECTION_CSS_MARKER in out
    assert VISIBLE_SECTION_CSS_CONTENT in out
    assert "book_iframe_jump.js" not in out
    assert "ca-jump-para" in out


def test_book_iframe_highlight_css_defines_visible_section_rule():
    css = (package_assets_dir() / "book_iframe_highlight.css").read_text(encoding="utf-8")
    assert VISIBLE_SECTION_CSS_MARKER in css
    assert 'content: "§ " attr(data-section-number)' in css
    assert "[data-paragraph-number]::before" in css


def test_annotated_paragraph_ids_match_display_numbers():
    """Anchor id suffix must equal the paragraph number suffix (1-based, not off-by-one)."""
    soup = BeautifulSoup(annotate_html_with_section_ids(FORMAT_B_FIXTURE), "html.parser")
    for node in soup.find_all(attrs={"data-paragraph-number": True}):
        para_num = node["data-paragraph-number"]
        section, para_n = para_num.rsplit(".", 1)
        expected_id = f"para-{section}-{para_n}"
        assert node.get("id") == expected_id, (
            f"id {node.get('id')!r} != {expected_id!r} "
            f"for data-paragraph-number={para_num!r}"
        )


def test_chunk_anchor_ids_exist_in_annotated_html():
    """RAG anchor_id must match a DOM id (fixes #4 off-by-one / merge skew)."""
    import tempfile

    html = FORMAT_B_FIXTURE
    annotated = annotate_html_with_section_ids(html)
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(annotated)
        path = Path(f.name)
    try:
        chunks = parse_html_path_to_chunks(path, chunk_size=0, chunk_overlap=0)
    finally:
        path.unlink(missing_ok=True)

    soup = BeautifulSoup(annotated, "html.parser")
    for chunk in chunks:
        assert chunk.anchor_id, chunk
        target = soup.find(id=chunk.anchor_id)
        assert target is not None, f"missing #{chunk.anchor_id} for {chunk.chunk_id}"
        body_text = target.get_text(strip=True)
        assert body_text, f"empty anchor body for {chunk.anchor_id}"

"""Tests for HTML outline parsing and chunking (Climate Academy book RAG)."""

from pathlib import Path

import pytest

from html_sectioning import (
    IndexedChunk,
    parse_book_html,
    parse_html_path_to_chunks,
    records_to_indexed_chunks,
    word_chunks,
)

PROTOTYPE = Path(Path(__file__).resolve().parents[1], "input", "sample_ca_book.html")


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


def test_word_chunks_overlap():
    text = "one two three four five six seven eight"
    parts = word_chunks(text, chunk_size=4, overlap=1)
    assert parts[0].split() == ["one", "two", "three", "four"]
    assert parts[1].split() == ["four", "five", "six", "seven"]
    assert "eight" in parts[-1]


def test_word_chunks_invalid_overlap_raises():
    with pytest.raises(ValueError):
        word_chunks("a b", chunk_size=2, overlap=2)


def test_indexed_chunks_contain_section_header():
    html = PROTOTYPE.read_text(encoding="utf-8")
    records = parse_book_html(html)
    chunks = records_to_indexed_chunks(records, chunk_size=50, chunk_overlap=8)
    assert isinstance(chunks[0], IndexedChunk)
    assert chunks[0].document.startswith("[§ ")
    assert "Foundations" in chunks[0].document or "greenhouse" in chunks[0].document.lower()


def test_parse_html_path_to_chunks_integration():
    chunks = parse_html_path_to_chunks(PROTOTYPE, chunk_size=30, chunk_overlap=5)
    assert len(chunks) >= len(parse_book_html(PROTOTYPE.read_text(encoding="utf-8")))

"""Non-overlapping phrase matching with longest-match preference."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

# Pre-compiled (pattern, phrase, entry_id) — built once in build_term_index.
CompiledPhrase = Tuple[re.Pattern[str], str, str]


@dataclass(frozen=True)
class TextMatch:
    start: int
    end: int
    surface: str
    phrase: str
    entry_id: str


def compile_phrase_patterns(
    sorted_phrases: Sequence[str],
    phrase_to_entry_id: Dict[str, str],
    *,
    ignore_case: bool,
    min_term_length: int,
) -> List[CompiledPhrase]:
    """Compile all phrase regexes once (annotate_book_html calls this thousands of times)."""
    flags = re.IGNORECASE if ignore_case else 0
    out: List[CompiledPhrase] = []
    for phrase in sorted_phrases:
        if len(phrase) < min_term_length or phrase.isdigit():
            continue
        lookup = phrase.lower() if ignore_case else phrase
        entry_id = phrase_to_entry_id.get(lookup)
        if entry_id is None:
            continue
        out.append(
            (re.compile(r"\b" + re.escape(phrase) + r"\b", flags), phrase, entry_id)
        )
    return out


def find_non_overlapping_matches(
    text: str,
    sorted_phrases: Sequence[str],
    phrase_to_entry_id: Dict[str, str],
    *,
    ignore_case: bool,
    min_term_length: int,
    compiled_phrases: Sequence[CompiledPhrase] | None = None,
) -> List[TextMatch]:
    if not text.strip():
        return []

    if compiled_phrases is None:
        compiled_phrases = compile_phrase_patterns(
            sorted_phrases,
            phrase_to_entry_id,
            ignore_case=ignore_case,
            min_term_length=min_term_length,
        )

    candidates: List[tuple] = []

    for pattern, phrase, entry_id in compiled_phrases:
        for match in pattern.finditer(text):
            candidates.append(
                (
                    match.start(),
                    match.end(),
                    match.group(0),
                    phrase,
                    entry_id,
                    match.end() - match.start(),
                )
            )

    candidates.sort(key=lambda row: (-row[5], row[0]))
    occupied = [False] * len(text)
    chosen: List[TextMatch] = []

    for start, end, surface, phrase, entry_id, _length in candidates:
        if any(occupied[start:end]):
            continue
        for idx in range(start, end):
            occupied[idx] = True
        chosen.append(
            TextMatch(
                start=start,
                end=end,
                surface=surface,
                phrase=phrase,
                entry_id=entry_id,
            )
        )

    chosen.sort(key=lambda m: m.start)
    return chosen

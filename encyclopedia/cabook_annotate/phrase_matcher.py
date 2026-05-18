"""Non-overlapping phrase matching with longest-match preference."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Sequence


@dataclass(frozen=True)
class TextMatch:
    start: int
    end: int
    surface: str
    phrase: str
    entry_id: str


def find_non_overlapping_matches(
    text: str,
    sorted_phrases: Sequence[str],
    phrase_to_entry_id: Dict[str, str],
    *,
    ignore_case: bool,
    min_term_length: int,
) -> List[TextMatch]:
    if not text.strip():
        return []

    flags = re.IGNORECASE if ignore_case else 0
    candidates: List[tuple] = []

    for phrase in sorted_phrases:
        if len(phrase) < min_term_length:
            continue
        pattern = re.compile(r"\b" + re.escape(phrase) + r"\b", flags)
        for match in pattern.finditer(text):
            lookup = phrase.lower() if ignore_case else phrase
            entry_id = phrase_to_entry_id.get(lookup)
            if entry_id is None:
                continue
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

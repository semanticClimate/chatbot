"""Expand encyclopedia surface forms (plurals; optional verb forms)."""

from __future__ import annotations

import re
from typing import Set


def expand_surface_forms(
    term: str,
    *,
    expand_plurals: bool,
    expand_verbs: bool,
    min_length: int,
) -> Set[str]:
    base = term.strip()
    if not base or len(base) < min_length:
        return set()

    forms: Set[str] = {base}
    if expand_plurals:
        forms.update(_plural_variants(base))
    if expand_verbs and " " not in base:
        forms.update(_verb_variants(base))
    return {f for f in forms if len(f) >= min_length}


def _plural_variants(term: str) -> Set[str]:
    out: Set[str] = set()
    lower = term.lower()

    if lower.endswith("y") and len(lower) > 2 and lower[-2] not in "aeiou":
        out.add(term[:-1] + "ies")
        out.add(term[:-1] + "y")
    elif lower.endswith(("s", "x", "z", "ch", "sh")):
        out.add(term + "es")
        out.add(re.sub(r"es$", "", term, flags=re.IGNORECASE))
    elif lower.endswith("s") and not lower.endswith("ss"):
        out.add(re.sub(r"s$", "", term, flags=re.IGNORECASE))
        out.add(term + "s")
    else:
        out.add(term + "s")

    return {v for v in out if v}


def _verb_variants(term: str) -> Set[str]:
    out: Set[str] = set()
    lower = term.lower()
    if len(lower) < 4:
        return out
    if lower.endswith("e"):
        out.add(term + "ing")
        out.add(term + "d")
    elif lower.endswith("y") and len(lower) > 2:
        out.add(term[:-1] + "ying")
        out.add(term[:-1] + "ied")
    else:
        out.add(term + "ing")
        out.add(term + "ed")
    return out

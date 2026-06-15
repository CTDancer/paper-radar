from __future__ import annotations

import math
import re
from difflib import SequenceMatcher


def compact(text: str) -> str:
    return " ".join((text or "").split())


def contains_any(text: str, terms: list[str]) -> bool:
    return any(term_matches(text, term) for term in terms)


def count_term_hits(text: str, terms: list[str]) -> int:
    return sum(1 for term in terms if term_matches(text, term))


def term_matches(text: str, term: str) -> bool:
    normalized = r"\s+".join(re.escape(part) for part in term.lower().split())
    pattern = re.compile(rf"(?<![a-z0-9]){normalized}(?![a-z0-9])", re.I)
    return bool(pattern.search(text or ""))


def fuzzy_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def citation_signal(count: int | None) -> float:
    if not count or count <= 0:
        return 0.0
    return min(3.0, math.log10(count + 1))

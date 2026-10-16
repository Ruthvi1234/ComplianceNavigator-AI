"""
Turns matched query terms in a text block into `<mark>` spans so the
frontend can render highlighted snippets and (Phase 2) highlighted overlays
in the PDF viewer once per-page text offsets are stored from OCR extraction.
"""
from __future__ import annotations

import re


def highlight_terms(text: str, query: str) -> str:
    terms = [re.escape(t) for t in query.split() if len(t) > 1]
    if not terms:
        return text
    pattern = re.compile(r"(" + "|".join(terms) + r")", re.IGNORECASE)
    return pattern.sub(r"<mark>\1</mark>", text)


def find_match_offsets(text: str, query: str) -> list[tuple[int, int]]:
    """Character offsets of query-term matches — the shape the PDF viewer's
    highlight overlay needs once page-level text offsets are stored."""
    terms = [re.escape(t) for t in query.split() if len(t) > 1]
    if not terms:
        return []
    pattern = re.compile(r"(" + "|".join(terms) + r")", re.IGNORECASE)
    return [(m.start(), m.end()) for m in pattern.finditer(text)]

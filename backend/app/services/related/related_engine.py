"""
Related-document recommendations.

Only waste-management documents are eligible.

Documents are compared using:

1. Keywords
2. Waste categories
3. Issuing authority
"""

from __future__ import annotations

from app.models.document import DocumentSearchHit
from app.services.search.engine import (
    IndexedDocument,
    search_engine,
)


# ============================================================
# VALID WASTE CATEGORIES
# ============================================================

VALID_WASTE_CATEGORIES = {
    "plastic",
    "e-waste",
    "battery",
    "hazardous",
    "solid waste",
    "biomedical",
    "construction & demolition",
}


# ============================================================
# AUTHORITY NORMALIZATION
# ============================================================

def _normalize_authority(
    authority: str | None,
) -> str:

    value = str(
        authority or ""
    ).strip()

    if not value:
        return ""

    authority_map = {
        "MOEFCC": "MoEFCC",
        "MOEF&CC": "MoEFCC",
        "MOEF CC": "MoEFCC",
        "MoEFCC": "MoEFCC",

        "CPCB": "CPCB",

        "KSPCB": "KSPCB",
    }

    return authority_map.get(
        value.upper(),
        value,
    )


# ============================================================
# NORMALIZATION HELPERS
# ============================================================

def _normalize(
    value,
) -> str:

    if value is None:
        return ""

    return str(value).strip().lower()


def _normalize_list(
    value,
) -> list[str]:

    if value is None:
        return []

    if isinstance(value, str):
        value = [value]

    try:
        return [
            _normalize(item)
            for item in value
            if item is not None
            and str(item).strip()
        ]
    except TypeError:
        return []


# ============================================================
# WASTE DOCUMENT CHECK
# ============================================================

def _is_waste_document(
    doc: IndexedDocument,
) -> bool:

    categories = set(
        _normalize_list(
            doc.waste_category
        )
    )

    return bool(
        categories
        & VALID_WASTE_CATEGORIES
    )


# ============================================================
# SIMILARITY
# ============================================================

def _similarity(
    a: IndexedDocument,
    b: IndexedDocument,
) -> float:

    keywords_a = set(
        _normalize_list(
            a.keywords
        )
    )

    keywords_b = set(
        _normalize_list(
            b.keywords
        )
    )

    categories_a = set(
        _normalize_list(
            a.waste_category
        )
    )

    categories_b = set(
        _normalize_list(
            b.waste_category
        )
    )

    authority_a = _normalize(
        a.authority
    )

    authority_b = _normalize(
        b.authority
    )

    set_a = (
        keywords_a
        | categories_a
    )

    set_b = (
        keywords_b
        | categories_b
    )

    if authority_a:
        set_a.add(
            f"authority:{authority_a}"
        )

    if authority_b:
        set_b.add(
            f"authority:{authority_b}"
        )

    if not set_a or not set_b:
        return 0.0

    intersection = len(
        set_a & set_b
    )

    union = len(
        set_a | set_b
    )

    if union == 0:
        return 0.0

    return intersection / union


# ============================================================
# RELATED DOCUMENTS
# ============================================================

def related_to(
    document_id: str,
    limit: int = 5,
) -> list[DocumentSearchHit]:

    # --------------------------------------------------------
    # Normalize limit
    # --------------------------------------------------------

    try:
        limit = int(limit)
    except (
        TypeError,
        ValueError,
    ):
        limit = 5

    limit = max(
        1,
        min(limit, 20),
    )

    # --------------------------------------------------------
    # Get documents
    # --------------------------------------------------------

    docs = (
        search_engine.all_documents()
    )

    # --------------------------------------------------------
    # Find target
    # --------------------------------------------------------

    target = next(
        (
            doc
            for doc in docs
            if str(doc.id)
            == str(document_id)
        ),
        None,
    )

    if target is None:
        return []

    # --------------------------------------------------------
    # Target must be waste-related
    # --------------------------------------------------------

    if not _is_waste_document(
        target
    ):
        return []

    # --------------------------------------------------------
    # Candidate documents
    # --------------------------------------------------------

    candidates = [
        doc
        for doc in docs
        if (
            str(doc.id)
            != str(document_id)
            and _is_waste_document(doc)
        )
    ]

    # --------------------------------------------------------
    # Score candidates
    # --------------------------------------------------------

    scored = []

    for doc in candidates:

        score = _similarity(
            target,
            doc,
        )

        if score > 0:

            scored.append(
                (
                    doc,
                    score,
                )
            )

    # --------------------------------------------------------
    # Sort
    # --------------------------------------------------------

    scored.sort(
        key=lambda item: (
            item[1],
            item[0].publication_date
            or "",
        ),
        reverse=True,
    )

    # --------------------------------------------------------
    # Build response
    # --------------------------------------------------------

    hits: list[
        DocumentSearchHit
    ] = []

    for doc, score in scored[:limit]:

        summary = (
            doc.summary
            or doc.title
            or ""
        )

        # IMPORTANT:
        # Convert MOEFCC -> MoEFCC
        # before Pydantic validation.
        authority = (
            _normalize_authority(
                doc.authority
            )
        )

        hit = DocumentSearchHit(
            id=doc.id,

            title=(
                doc.title
                or ""
            ),

            original_title=None,

            authority=authority,

            document_type=(
                doc.document_type
                or ""
            ),

            waste_category=(
                doc.waste_category
                or []
            ),

            state=doc.state,

            publication_date=(
                doc.publication_date
                or None
            ),

            reference_code=(
                doc.reference_code
                or ""
            ),

            snippet=summary[:160],

            content_text=(
                doc.content_text
                or ""
            ),

            score=round(
                score,
                4,
            ),

            source_url=(
                doc.source_url
                or ""
            ),

            file_url=doc.file_url,

            page_count=(
                doc.page_count
            ),

            keywords=(
                doc.keywords
                or []
            ),
        )

        hits.append(hit)

    return hits
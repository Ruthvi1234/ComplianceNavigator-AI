from fastapi import APIRouter, HTTPException, Query

from app.services.highlight.highlighter import highlight_terms
from app.services.related.related_engine import related_to
from app.services.search.engine import search_engine


router = APIRouter(
    prefix="/documents",
    tags=["documents"],
)


# ============================================================
# GET DOCUMENT
# ============================================================

@router.get("/{document_id}")
async def get_document(document_id: str):

    doc = next(
        (
            d
            for d in search_engine._docs
            if d.id == document_id
        ),
        None,
    )

    if doc is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    return {
        "id": doc.id,
        "title": doc.title or "",
        "authority": doc.authority or "",

        "documentType": (
            doc.document_type or ""
        ),

        "wasteCategory": (
            doc.waste_category or []
        ),

        "state": doc.state,

        "publicationDate": (
            doc.publication_date or None
        ),

        "referenceCode": (
            doc.reference_code or ""
        ),

        "keywords": (
            doc.keywords or []
        ),

        "summary": (
            doc.summary or ""
        ),

        "sourceUrl": (
            doc.source_url or ""
        ),

        "fileUrl": doc.file_url,

        "pageCount": doc.page_count,
    }


# ============================================================
# GET HIGHLIGHTED SNIPPET
# ============================================================

@router.get("/{document_id}/highlighted")
async def get_highlighted_snippet(
    document_id: str,
    q: str = Query(
        "",
        description="Query to highlight",
    ),
):

    doc = next(
        (
            d
            for d in search_engine._docs
            if d.id == document_id
        ),
        None,
    )

    if doc is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    summary = (
        doc.summary
        or doc.title
        or ""
    )

    return {
        "id": doc.id,
        "highlightedHtml": highlight_terms(
            summary,
            q,
        ),
    }


# ============================================================
# GET RELATED DOCUMENTS
# ============================================================

@router.get("/{document_id}/related")
async def get_related(
    document_id: str,
    limit: int = Query(
        5,
        ge=1,
        le=20,
    ),
):

    # --------------------------------------------------------
    # Verify document exists first
    # --------------------------------------------------------

    target = next(
        (
            doc
            for doc in search_engine._docs
            if doc.id == document_id
        ),
        None,
    )

    if target is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    # --------------------------------------------------------
    # Safely calculate related documents
    # --------------------------------------------------------

    try:

        results = related_to(
            document_id=document_id,
            limit=limit,
        )

        # Make sure FastAPI always gets a list.
        if results is None:
            return []

        return results

    except Exception as exc:

        # IMPORTANT:
        # Print the real error in the backend terminal.
        print(
            "ERROR in related_to():",
            repr(exc),
        )

        # Return an HTTP error containing the actual
        # Python exception instead of the useless
        # "Internal Server Error".
        raise HTTPException(
            status_code=500,
            detail=(
                "Related lookup failed: "
                f"{type(exc).__name__}: {exc}"
            ),
        )
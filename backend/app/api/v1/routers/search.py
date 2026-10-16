"""
Core search endpoint. Thin by design: validates the request, calls the
search engine, logs analytics, returns results. No ranking logic lives here.
"""
from fastapi import APIRouter

from app.schemas.search import SearchRequest, SearchResponse
from app.services.analytics.search_analytics import record_search
from app.services.search.engine import search_engine

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search(payload: SearchRequest) -> SearchResponse:
    hits, total, took_ms = search_engine.search(
        query=payload.query,
        filters=payload.filters,
        page=payload.page,
        page_size=payload.page_size,
    )
    await record_search(
        query=payload.query,
        result_count=total,
        filters=payload.filters.model_dump(exclude_none=True) if payload.filters else None,
    )
    return SearchResponse(
        query=payload.query,
        total=total,
        page=payload.page,
        page_size=payload.page_size,
        results=hits,
        took_ms=took_ms,
    )


@router.get("/suggest")
async def suggest(q: str) -> list[str]:
    """Lightweight autocomplete: prefix-match against indexed titles/keywords."""
    q_lower = q.lower().strip()
    if not q_lower:
        return []
    candidates: set[str] = set()
    for doc in search_engine._docs:
        for term in [doc.title, *doc.keywords]:
            if term.lower().startswith(q_lower):
                candidates.add(term)
    return sorted(candidates)[:8]

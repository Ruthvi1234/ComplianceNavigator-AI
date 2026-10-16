"""
Search analytics: records every query + filter combination and result count
so the dashboard can show popular searches, zero-result queries (a proxy for
crawl gaps), and category/authority breakdowns.

Phase 1: writes to Mongo if available; the router falls back to serving the
in-memory `_recent` buffer when Mongo isn't reachable, so the analytics
dashboard has something real to show in the standalone demo too.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime

_recent: list[dict] = []  # process-local fallback buffer, most-recent-first
_MAX_BUFFER = 500


async def record_search(query: str, result_count: int, filters: dict | None = None) -> None:
    entry = {
        "query": query,
        "result_count": result_count,
        "filters": filters or {},
        "timestamp": datetime.utcnow().isoformat(),
    }
    _recent.insert(0, entry)
    del _recent[_MAX_BUFFER:]

    try:
        from app.db.mongo import get_db

        await get_db().search_log.insert_one(entry)
    except Exception:
        # Mongo not running in this environment — the in-memory buffer above
        # keeps the analytics endpoint functional regardless.
        pass


def get_popular_queries(limit: int = 10) -> list[dict]:
    counts = Counter(e["query"].lower() for e in _recent if e["query"].strip())
    return [{"query": q, "count": c} for q, c in counts.most_common(limit)]


def get_zero_result_queries(limit: int = 10) -> list[dict]:
    seen = []
    for e in _recent:
        if e["result_count"] == 0 and e["query"] not in [s["query"] for s in seen]:
            seen.append({"query": e["query"], "timestamp": e["timestamp"]})
        if len(seen) >= limit:
            break
    return seen


def get_summary() -> dict:
    return {
        "total_searches": len(_recent),
        "popular_queries": get_popular_queries(),
        "zero_result_queries": get_zero_result_queries(),
    }

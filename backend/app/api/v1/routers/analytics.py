from collections import Counter

from fastapi import APIRouter

from app.services.analytics.search_analytics import get_summary
from app.services.search.engine import search_engine
from app.workers.auto_updater import state as auto_updater_state

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/search-summary")
async def search_summary():
    raw = get_summary()
    docs = search_engine.all_documents()

    authority_counts = Counter(d.authority for d in docs)
    category_counts = Counter(cat for d in docs for cat in d.waste_category)

    crawler_status = []
    if auto_updater_state.last_summary:
        for authority, info in auto_updater_state.last_summary.items():
            crawler_status.append({
                "authority": authority,
                "lastRun": auto_updater_state.last_finished_at,
                "documentsFound": info.get("found", 0),
                "status": "ok" if info.get("status") == "ok" else "error",
            })

    return {
        "totalSearches": raw["total_searches"],
        "popularQueries": [
            {"query": q["query"], "count": q["count"]}
            for q in raw["popular_queries"]
        ],
        "zeroResultQueries": raw["zero_result_queries"],
        "authorityBreakdown": [
            {"authority": authority, "count": count}
            for authority, count in authority_counts.items()
        ],
        "categoryBreakdown": [
            {"category": category, "count": count}
            for category, count in category_counts.items()
        ],
        "crawlerStatus": crawler_status,
        "indexedDocuments": len(docs),
    }
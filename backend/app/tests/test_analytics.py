import asyncio

from app.services.analytics import search_analytics


def test_record_and_summarize_search():
    search_analytics._recent.clear()
    asyncio.run(search_analytics.record_search("plastic epr", result_count=3))
    asyncio.run(search_analytics.record_search("plastic epr", result_count=3))
    asyncio.run(search_analytics.record_search("unknown material xyz", result_count=0))

    summary = search_analytics.get_summary()
    assert summary["total_searches"] == 3
    assert summary["popular_queries"][0] == {"query": "plastic epr", "count": 2}
    assert any(q["query"] == "unknown material xyz" for q in summary["zero_result_queries"])

from app.schemas.search import SearchFilters
from app.services.search.engine import search_engine


def test_search_returns_relevant_top_result():
    hits, total, _ = search_engine.search("plastic packaging EPR", filters=None, page=1, page_size=5)
    assert total > 0
    assert hits[0].reference_code == "MoEFCC/2024/PWM-07"


def test_search_empty_query_still_paginates():
    hits, total, _ = search_engine.search("", filters=None, page=1, page_size=3)
    assert total == 6
    assert len(hits) == 3


def test_filter_by_authority_excludes_others():
    filters = SearchFilters(authority=["KSPCB"])  # type: ignore[arg-type]
    hits, total, _ = search_engine.search("waste", filters=filters, page=1, page_size=10)
    assert total > 0
    assert all(h.authority == "KSPCB" for h in hits)


def test_filter_by_state_excludes_central_docs():
    filters = SearchFilters(state="Karnataka")
    hits, total, _ = search_engine.search("", filters=filters, page=1, page_size=10)
    assert total > 0
    assert all(h.state == "Karnataka" for h in hits)


def test_pagination_respects_page_size():
    hits, total, _ = search_engine.search("waste", filters=None, page=2, page_size=2)
    assert len(hits) <= 2

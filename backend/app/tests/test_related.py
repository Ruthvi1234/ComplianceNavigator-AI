from app.services.related.related_engine import related_to


def test_related_excludes_the_source_document():
    related = related_to("seed-001", limit=5)
    assert all(r.id != "seed-001" for r in related)


def test_related_returns_documents_sharing_authority_or_category():
    related = related_to("seed-002", limit=5)  # CPCB E-Waste doc
    assert len(related) > 0
    # every related hit should share at least authority or a keyword-derived signal
    assert any(r.authority == "CPCB" for r in related)


def test_related_unknown_document_returns_empty():
    assert related_to("does-not-exist", limit=5) == []

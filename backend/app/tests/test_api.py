from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_search_endpoint_returns_ranked_results():
    res = client.post("/api/v1/search", json={"query": "hazardous waste karnataka", "page": 1, "page_size": 5})
    assert res.status_code == 200
    body = res.json()
    assert body["total"] >= 1
    assert body["results"][0]["authority"] == "KSPCB"


def test_document_detail_endpoint():
    res = client.get("/api/v1/documents/seed-003")
    assert res.status_code == 200
    assert res.json()["reference_code"] == "KSPCB/2024/HW-021"


def test_document_not_found_returns_404():
    res = client.get("/api/v1/documents/does-not-exist")
    assert res.status_code == 404


def test_related_endpoint():
    res = client.get("/api/v1/documents/seed-001/related")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_analytics_endpoint():
    res = client.get("/api/v1/analytics/search-summary")
    assert res.status_code == 200
    assert "popular_queries" in res.json()

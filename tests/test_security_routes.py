from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_llm_diagnostics_require_authentication():
    assert client.get("/health/llm/config").status_code == 401
    assert client.get("/health/llm").status_code == 401


def test_legacy_comment_read_requires_authentication():
    response = client.get(
        "/threads/988be0e0-22aa-40be-b857-1a4f545d4863/comments",
        params={"message_index": 0},
    )
    assert response.status_code == 401


def test_security_headers_are_set():
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"


def test_untrusted_browser_origin_is_rejected_for_refresh():
    response = client.post(
        "/auth/refresh",
        headers={"Origin": "https://attacker.example", "Sec-Fetch-Site": "cross-site"},
    )
    assert response.status_code == 403

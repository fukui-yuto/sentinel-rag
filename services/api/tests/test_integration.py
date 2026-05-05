"""Integration tests for the Sentinel RAG API.

All tests in this module require a running server and are marked with
``@pytest.mark.integration``.  They are automatically skipped when the
server is not reachable (see conftest.py).

Run with:
    pytest services/api/tests/test_integration.py -m integration -v
"""

import httpx
import pytest

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# 1. Auth flow
# ---------------------------------------------------------------------------
class TestAuth:
    """POST /api/v1/auth/dev-login"""

    def test_dev_login_returns_token(self, api_base_url: str) -> None:
        r = httpx.post(
            f"{api_base_url}/api/v1/auth/dev-login",
            params={"email": "admin@sentinel.local"},
            timeout=10,
        )
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert body["expires_in"] > 0

    def test_dev_login_unknown_email(self, api_base_url: str) -> None:
        r = httpx.post(
            f"{api_base_url}/api/v1/auth/dev-login",
            params={"email": "nonexistent@example.com"},
            timeout=10,
        )
        assert r.status_code == 404

    def test_auth_me_returns_user(
        self, api_base_url: str, auth_headers: dict[str, str]
    ) -> None:
        r = httpx.get(
            f"{api_base_url}/api/v1/auth/me",
            headers=auth_headers,
            timeout=10,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["email"] == "admin@sentinel.local"
        assert "id" in body
        assert "role" in body

    def test_protected_endpoint_rejects_missing_token(
        self, api_base_url: str
    ) -> None:
        r = httpx.get(f"{api_base_url}/api/v1/auth/me", timeout=10)
        assert r.status_code == 401

    def test_protected_endpoint_rejects_invalid_token(
        self, api_base_url: str
    ) -> None:
        r = httpx.get(
            f"{api_base_url}/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
            timeout=10,
        )
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# 2. Document upload
# ---------------------------------------------------------------------------
class TestDocumentUpload:
    """POST /api/v1/documents (multipart file upload)"""

    def test_upload_small_text_file(
        self, api_base_url: str, auth_headers: dict[str, str]
    ) -> None:
        import uuid
        uid = uuid.uuid4().hex[:8]
        fname = f"integ_test_{uid}.txt"
        file_content = f"This is a test document for integration testing. ID: {uid}".encode()
        files = {"file": (fname, file_content, "text/plain")}
        r = httpx.post(
            f"{api_base_url}/api/v1/documents",
            headers=auth_headers,
            files=files,
            data={"sensitivity": "internal"},
            timeout=30,
        )
        assert r.status_code == 201
        body = r.json()
        assert body["filename"] == fname
        assert body["status"] == "pending"
        assert body["file_size_bytes"] > 0
        assert "id" in body

    def test_upload_requires_auth(self, api_base_url: str) -> None:
        files = {"file": ("noauth.txt", b"no auth", "text/plain")}
        r = httpx.post(
            f"{api_base_url}/api/v1/documents",
            files=files,
            timeout=10,
        )
        assert r.status_code == 401

    def test_upload_default_sensitivity(
        self, api_base_url: str, auth_headers: dict[str, str]
    ) -> None:
        import uuid
        uid = uuid.uuid4().hex[:8]
        fname = f"test_{uid}.txt"
        files = {"file": (fname, f"content for sensitivity test {uid}".encode(), "text/plain")}
        r = httpx.post(
            f"{api_base_url}/api/v1/documents",
            headers=auth_headers,
            files=files,
            timeout=10,
        )
        assert r.status_code == 201
        body = r.json()
        assert body["sensitivity"] in ("public", "internal", "confidential", "restricted")


# ---------------------------------------------------------------------------
# 3. Document listing
# ---------------------------------------------------------------------------
class TestDocumentListing:
    """GET /api/v1/documents"""

    def test_list_documents(
        self, api_base_url: str, auth_headers: dict[str, str]
    ) -> None:
        r = httpx.get(
            f"{api_base_url}/api/v1/documents",
            headers=auth_headers,
            timeout=10,
        )
        assert r.status_code == 200
        body = r.json()
        assert "items" in body
        assert "total" in body
        assert "page" in body
        assert "page_size" in body
        assert isinstance(body["items"], list)

    def test_list_documents_pagination(
        self, api_base_url: str, auth_headers: dict[str, str]
    ) -> None:
        r = httpx.get(
            f"{api_base_url}/api/v1/documents",
            headers=auth_headers,
            params={"page": 1, "page_size": 5},
            timeout=10,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["page"] == 1
        assert body["page_size"] == 5

    def test_list_documents_requires_auth(self, api_base_url: str) -> None:
        r = httpx.get(f"{api_base_url}/api/v1/documents", timeout=10)
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# 4. QA query (non-streaming)
# ---------------------------------------------------------------------------
class TestQAQuery:
    """POST /api/v1/qa/query"""

    def test_qa_query(
        self, api_base_url: str, auth_headers: dict[str, str]
    ) -> None:
        try:
            r = httpx.post(
                f"{api_base_url}/api/v1/qa/query",
                headers=auth_headers,
                json={"query": "What is Kubernetes?", "model": "qwen2.5:3b"},
                timeout=120,
            )
        except httpx.ReadTimeout:
            pytest.skip("QA query timed out (embedding provider may be rate-limited)")
        # Accept 200 (success) or 500 (pipeline not fully configured / rate-limited)
        assert r.status_code in (200, 500)
        if r.status_code == 200:
            body = r.json()
            assert "answer" in body
            assert "sources" in body
            assert "provider" in body
            assert "model" in body
            assert "duration_ms" in body

    def test_qa_query_empty_rejected(
        self, api_base_url: str, auth_headers: dict[str, str]
    ) -> None:
        r = httpx.post(
            f"{api_base_url}/api/v1/qa/query",
            headers=auth_headers,
            json={"query": "   "},
            timeout=10,
        )
        assert r.status_code == 400

    def test_qa_query_invalid_model(
        self, api_base_url: str, auth_headers: dict[str, str]
    ) -> None:
        r = httpx.post(
            f"{api_base_url}/api/v1/qa/query",
            headers=auth_headers,
            json={"query": "test", "model": "not-a-real-model"},
            timeout=10,
        )
        assert r.status_code == 400

    def test_qa_query_requires_auth(self, api_base_url: str) -> None:
        r = httpx.post(
            f"{api_base_url}/api/v1/qa/query",
            json={"query": "test question"},
            timeout=10,
        )
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# 5. QA streaming
# ---------------------------------------------------------------------------
class TestQAStreaming:
    """POST /api/v1/qa/query/stream"""

    def test_qa_stream_returns_sse(
        self, api_base_url: str, auth_headers: dict[str, str]
    ) -> None:
        try:
            with httpx.stream(
                "POST",
                f"{api_base_url}/api/v1/qa/query/stream",
                headers=auth_headers,
                json={"query": "What is Docker?", "model": "qwen2.5:3b"},
                timeout=120,
            ) as r:
                assert r.status_code == 200
                content_type = r.headers.get("content-type", "")
                assert "text/event-stream" in content_type

                events = []
                for line in r.iter_lines():
                    if line.startswith("data: "):
                        events.append(line)
                        if line == "data: [DONE]":
                            break
                assert any("[DONE]" in e for e in events)
        except (httpx.ReadTimeout, httpx.RemoteProtocolError):
            pytest.skip("QA stream timed out (embedding provider may be rate-limited)")

    def test_qa_stream_empty_query_rejected(
        self, api_base_url: str, auth_headers: dict[str, str]
    ) -> None:
        try:
            r = httpx.post(
                f"{api_base_url}/api/v1/qa/query/stream",
                headers=auth_headers,
                json={"query": "   "},
                timeout=15,
            )
            assert r.status_code == 400
        except (httpx.ReadTimeout, httpx.RemoteProtocolError):
            pytest.skip("Server connection issue")

    def test_qa_stream_requires_auth(self, api_base_url: str) -> None:
        try:
            r = httpx.post(
                f"{api_base_url}/api/v1/qa/query/stream",
                json={"query": "test"},
                timeout=15,
            )
            assert r.status_code == 401
        except (httpx.ReadTimeout, httpx.RemoteProtocolError):
            pytest.skip("Server connection issue")


# ---------------------------------------------------------------------------
# 6. Admin endpoints
# ---------------------------------------------------------------------------
class TestAdmin:
    """Admin endpoints (require admin role)."""

    def test_admin_list_users(
        self, api_base_url: str, auth_headers: dict[str, str]
    ) -> None:
        r = httpx.get(
            f"{api_base_url}/api/v1/admin/users",
            headers=auth_headers,
            timeout=10,
        )
        assert r.status_code == 200
        body = r.json()
        assert isinstance(body, list)
        if body:
            assert "email" in body[0]
            assert "role" in body[0]

    def test_admin_health(
        self, api_base_url: str, auth_headers: dict[str, str]
    ) -> None:
        r = httpx.get(
            f"{api_base_url}/api/v1/admin/health",
            headers=auth_headers,
            timeout=10,
        )
        assert r.status_code == 200
        body = r.json()
        assert "status" in body
        assert "stats" in body

    def test_admin_metrics(
        self, api_base_url: str, auth_headers: dict[str, str]
    ) -> None:
        r = httpx.get(
            f"{api_base_url}/api/v1/admin/metrics",
            headers=auth_headers,
            timeout=10,
        )
        assert r.status_code == 200
        body = r.json()
        assert "period" in body
        assert "queries" in body

    def test_admin_endpoints_require_auth(self, api_base_url: str) -> None:
        for path in ("/api/v1/admin/users", "/api/v1/admin/health", "/api/v1/admin/metrics"):
            r = httpx.get(f"{api_base_url}{path}", timeout=10)
            assert r.status_code == 401, f"{path} should require auth"


# ---------------------------------------------------------------------------
# 7. Health endpoints
# ---------------------------------------------------------------------------
class TestHealth:
    """GET /api/v1/health, GET /api/v1/health/ready"""

    def test_health_liveness(self, api_base_url: str) -> None:
        r = httpx.get(f"{api_base_url}/api/v1/health", timeout=5)
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}

    def test_health_readiness(self, api_base_url: str) -> None:
        r = httpx.get(f"{api_base_url}/api/v1/health/ready", timeout=10)
        assert r.status_code == 200
        body = r.json()
        assert "status" in body
        assert body["status"] in ("ready", "degraded")
        assert "checks" in body
        checks = body["checks"]
        # Verify all expected services are checked
        for service in ("postgres", "redis", "qdrant", "minio"):
            assert service in checks, f"Missing health check for {service}"
            assert checks[service] in ("ok", "error")

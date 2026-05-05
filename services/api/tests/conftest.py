"""Shared fixtures for integration tests.

Integration tests are marked with @pytest.mark.integration and require
a running Sentinel RAG server.  They are skipped automatically when the
server is unreachable.
"""

import httpx
import pytest

API_BASE_URL = "http://localhost:8000"
DEV_LOGIN_EMAIL = "admin@sentinel.local"


def _server_is_reachable() -> bool:
    """Return True if the API server responds to the health endpoint."""
    try:
        r = httpx.get(f"{API_BASE_URL}/api/v1/health", timeout=3)
        return r.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException, OSError):
        return False


_reachable = _server_is_reachable()


def pytest_collection_modifyitems(config, items):  # noqa: ANN001, ANN201
    """Auto-skip integration tests when the server is not available."""
    if _reachable:
        return
    skip_marker = pytest.mark.skip(reason="API server not reachable – skipping integration tests")
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_marker)


@pytest.fixture(scope="session")
def api_base_url() -> str:
    return API_BASE_URL


@pytest.fixture(scope="session")
def auth_token() -> str:
    """Obtain a JWT token via the dev-login endpoint (session-scoped)."""
    if not _reachable:
        pytest.skip("API server not reachable")
    r = httpx.post(
        f"{API_BASE_URL}/api/v1/auth/dev-login",
        params={"email": DEV_LOGIN_EMAIL},
        timeout=10,
    )
    assert r.status_code == 200, f"Dev login failed: {r.status_code} {r.text}"
    data = r.json()
    return data["access_token"]


@pytest.fixture(scope="session")
def auth_headers(auth_token: str) -> dict[str, str]:
    """Authorization headers with the Bearer token."""
    return {"Authorization": f"Bearer {auth_token}"}

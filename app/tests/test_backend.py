"""
Integration test for live backend connectivity.
Skipped by default — run with: pytest -m integration
"""
import pytest
from app.services.backend_client import get


@pytest.mark.integration
def test_connection():
    """Verify the deployed backend is reachable and returns running status."""
    status = get("/")
    print("Backend Status:", status)
    assert status.get("status") in ("running", "ok")


if __name__ == "__main__":
    test_connection()

"""Tests for Handler Service."""
import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from services.handler.service import app

client = TestClient(app)


def test_health_check():
    """Test the health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] in ["handler", "handler"]


def test_logs_endpoint():
    """Test logs endpoint."""
    response = client.get("/logs?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_metrics_endpoint():
    """Test metrics endpoint."""
    response = client.get("/metrics?period=60")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data



def test_handle_general_query():
    """Test handling a general query."""
    response = client.post("/handle", json={
        "phone": "+1234567890",
        "account_id": "test_user",
        "text": "Hello, can you help me?",
        "verified": False
    })
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert "session_verified" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

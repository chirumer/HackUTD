"""Tests for Writeops Service."""
import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from services.writeops.service import app

client = TestClient(app)


def test_health_check():
    """Test the health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] in ["writeops", "writeops"]


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


# Add service-specific tests here

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

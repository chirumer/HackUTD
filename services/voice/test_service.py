"""Tests for Voice Service."""
import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi.testclient import TestClient
from services.voice.service import app

client = TestClient(app)


def test_health_check():
    """Test the health endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "voice"


def test_transcribe():
    """Test STT transcription."""
    import base64
    
    # Simulate audio bytes
    fake_audio = b"fake_audio_data"
    audio_b64 = base64.b64encode(fake_audio).decode("ascii")
    
    response = client.post("/transcribe", json={
        "audio_bytes": audio_b64,
        "format": "wav"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "transcript" in data
    assert isinstance(data["transcript"], str)


def test_synthesize():
    """Test TTS synthesis."""
    response = client.post("/synthesize", json={
        "text": "Hello, this is a test"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "audio_bytes" in data
    assert "format" in data
    assert data["format"] == "wav"


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
    assert data["service"] == "voice"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

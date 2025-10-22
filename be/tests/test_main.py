"""Test main application endpoints and initialization."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def test_read_root(client):
    """Test root endpoint returns welcome message."""
    response = client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["message"] == "Welcome to Sudar API"
    assert payload["version"] == "1.0.0"
    assert payload["status"] == "running"


def test_health_endpoint(client):
    """Test health check endpoint returns healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

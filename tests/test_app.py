"""
Test suite for FirstVoice Emergency Response API.

Mocks all Google Cloud SDKs to enable isolated unit testing
without requiring real GCP credentials or network access.
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ── Mock ALL Google Cloud SDKs before app import ──────────────────────────────
patch("google.cloud.logging.Client").start()
patch("google.cloud.secretmanager.SecretManagerServiceClient").start()
patch("google.cloud.error_reporting.Client").start()
patch("google.cloud.firestore.Client").start()

# Set test environment variables
os.environ["GEMINI_API_KEY"] = "test_api_key"
os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"

from app import app, limiter  # noqa: E402


@pytest.fixture
def client():
    """Provide a Flask test client with rate limiting disabled."""
    app.config["TESTING"] = True
    limiter.enabled = False
    with app.test_client() as test_client:
        yield test_client


# ─── Route Tests ───────────────────────────────────────────────────────────────

def test_index_loads(client):
    """Test that the main page renders with 200 OK."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"FirstVoice" in response.data


def test_analyze_no_payload(client):
    """Test 400/415 when no JSON body is provided."""
    response = client.post("/analyze", json=None)
    assert response.status_code in (400, 415)


def test_analyze_empty_text(client):
    """Test Pydantic rejects empty text."""
    response = client.post("/analyze", json={"text": ""})
    assert response.status_code == 400
    assert b"Description is required" in response.data


def test_analyze_text_too_long(client):
    """Test Pydantic rejects text over 1000 characters."""
    response = client.post("/analyze", json={"text": "x" * 1001})
    assert response.status_code == 400


@patch("google.genai.Client")
def test_analyze_success(mock_genai_class, client):
    """Test a successful end-to-end analysis with a mocked Gemini response."""
    mock_instance = mock_genai_class.return_value
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "detectedLanguage": "English",
        "emergencyType": "Cardiac Arrest",
        "severity": "CRITICAL",
        "steps": [{"step": 1, "action": "Call 112", "detail": "State location"}],
        "doNot": ["Do not move the person"],
        "dispatchSummary": "Adult collapsed, CPR started.",
        "reassurance": "Help is on the way.",
    })
    mock_instance.models.generate_content.return_value = mock_response

    response = client.post("/analyze", json={"text": "My friend collapsed!"})

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["emergencyType"] == "Cardiac Arrest"
    assert data["severity"] == "CRITICAL"


@patch("google.genai.Client")
def test_analyze_quota_exceeded(mock_genai_class, client):
    """Test that a 429 error from Gemini returns a user-friendly message."""
    mock_instance = mock_genai_class.return_value
    mock_instance.models.generate_content.side_effect = Exception("429 RESOURCE_EXHAUSTED")

    response = client.post("/analyze", json={"text": "Someone is choking!"})

    assert response.status_code == 429
    data = json.loads(response.data)
    assert "quota" in data["error"].lower()


@patch("google.genai.Client")
def test_security_headers_present(mock_genai_class, client):
    """Test that security headers are attached to every response."""
    response = client.get("/")
    assert "X-Frame-Options" in response.headers
    assert "X-Content-Type-Options" in response.headers
    assert "Content-Security-Policy" in response.headers

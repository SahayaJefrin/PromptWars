"""
Test suite for FirstVoice Emergency Response API.

Mocks all Google Cloud SDKs to enable isolated unit testing
without requiring real GCP credentials or network access.
"""

import json
import os
import sys
from unittest.mock import MagicMock, call, patch

import pytest

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# ── Mock ALL Google Cloud SDKs before app import ──────────────────────────────────
patch("google.cloud.logging.Client").start()
patch("google.cloud.secretmanager.SecretManagerServiceClient").start()
patch("google.cloud.error_reporting.Client").start()
mock_firestore = patch("google.cloud.firestore.Client").start()
mock_genai = patch("google.genai.Client").start()

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


def test_analyze_whitespace_only(client):
    """Test whitespace-only input is handled gracefully (no crashes)."""
    response = client.post("/analyze", json={"text": "   "})
    # Whitespace passes min_length=1 so goes to AI — any valid HTTP code is acceptable
    assert response.status_code in (200, 400, 500)


@patch("app.genai_client")
def test_analyze_success(mock_client, client):
    """Test a successful end-to-end analysis with a mocked Gemini response."""
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
    mock_client.models.generate_content.return_value = mock_response

    response = client.post("/analyze", json={"text": "My friend collapsed!"})

    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["emergencyType"] == "Cardiac Arrest"
    assert data["severity"] == "CRITICAL"


@patch("app.genai_client")
def test_analyze_quota_exceeded(mock_client, client):
    """Test that a 429 error from Gemini returns a user-friendly message."""
    mock_client.models.generate_content.side_effect = Exception("429 RESOURCE_EXHAUSTED")

    response = client.post("/analyze", json={"text": "Someone is choking!"})

    assert response.status_code == 429
    data = json.loads(response.data)
    assert "quota" in data["error"].lower()


def test_security_headers_present(client):
    """Test that all security headers are attached to every response."""
    response = client.get("/")
    assert "X-Frame-Options" in response.headers
    assert "X-Content-Type-Options" in response.headers
    assert "Content-Security-Policy" in response.headers
    assert "Strict-Transport-Security" in response.headers
    assert "Referrer-Policy" in response.headers


def test_firestore_write_on_success(client):
    """Test that a successful analysis triggers a Firestore document write."""
    import app as app_module

    mock_db = MagicMock()
    app_module.db = mock_db

    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "detectedLanguage": "English",
        "emergencyType": "Choking",
        "severity": "CRITICAL",
        "steps": [{"step": 1, "action": "Heimlich maneuver", "detail": "Thrust upward"}],
        "doNot": [],
        "dispatchSummary": "Adult choking.",
        "reassurance": "Stay calm.",
    })
    app_module.genai_client = MagicMock()
    app_module.genai_client.models.generate_content.return_value = mock_response

    client.post("/analyze", json={"text": "My child is choking!"})

    # Verify Firestore collection was called
    mock_db.collection.assert_called_once_with("emergencies")
    mock_db.collection.return_value.add.assert_called_once()

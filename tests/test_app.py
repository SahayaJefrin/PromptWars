import pytest
import json
import os
import sys
from unittest.mock import patch, MagicMock

# Add parent directory to path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock Google Cloud SDKs BEFORE importing app
mock_logging = patch('google.cloud.logging.Client').start()
mock_secret = patch('google.cloud.secretmanager.SecretManagerServiceClient').start()
mock_error = patch('google.cloud.error_reporting.Client').start()

# Set env vars for tests
os.environ["GEMINI_API_KEY"] = "test_key"
os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project"

from app import app, limiter

# Disable rate limits globally for tests
limiter.enabled = False

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_route(client):
    """Test standard main page loading."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"FirstVoice" in response.data

def test_analyze_no_data(client):
    """Test error when no JSON payload is sent."""
    response = client.post("/analyze", json=None)
    assert response.status_code in (400, 415)

def test_analyze_empty_text(client):
    """Test Pydantic validation for empty string."""
    response = client.post("/analyze", json={"text": ""})
    assert response.status_code == 400
    assert b"Invalid input" in response.data

def test_analyze_payload_too_long(client):
    """Test Pydantic validation for string > 1000 chars."""
    response = client.post("/analyze", json={"text": "a" * 1005})
    assert response.status_code == 400
    assert b"Invalid input" in response.data

@patch('app.genai_client.models.generate_content')
def test_analyze_success(mock_generate_content, client):
    """Test successful AI analysis cycle."""
    # Mock the Gemini response
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "detectedLanguage": "English",
        "emergencyType": "Cardiac Arrest",
        "severity": "CRITICAL",
        "steps": [{"step": 1, "action": "Call 112", "detail": ""}]
    })
    mock_generate_content.return_value = mock_response

    response = client.post("/analyze", json={"text": "My friend collapsed!"})
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data["emergencyType"] == "Cardiac Arrest"

@patch('app.genai_client.models.generate_content')
def test_analyze_api_failure(mock_generate_content, client):
    """Test handling of API-specific 429 errors."""
    mock_generate_content.side_effect = Exception("429 RESOURCE_EXHAUSTED")

    response = client.post("/analyze", json={"text": "Test error block"})
    
    assert response.status_code == 429
    assert b"Gemini AI Quota Exceeded" in response.data

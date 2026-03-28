import pytest
import json
import os
import sys
from unittest.mock import patch, MagicMock

# Add parent directory to path so we can import app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set API KEY for tests before importing app
os.environ["GEMINI_API_KEY"] = "test_key"
from app import app, limiter

# Disable rate limits globally for tests
limiter.enabled = False

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_index_route(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"FirstVoice" in response.data

def test_analyze_no_data(client):
    response = client.post("/analyze", json=None)
    # the test client might interpret json=None as an empty payload
    assert response.status_code in (400, 415)

def test_analyze_empty_text(client):
    response = client.post("/analyze", json={"text": "   "})
    assert response.status_code == 400
    assert b"Emergency description is required" in response.data

def test_analyze_payload_too_long(client):
    response = client.post("/analyze", json={"text": "a" * 1005})
    assert response.status_code == 400
    assert b"Description is too long" in response.data

@patch('app.client.models.generate_content')
def test_analyze_success(mock_generate_content, client):
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
    assert data["severity"] == "CRITICAL"
    assert len(data["steps"]) == 1

@patch('app.client.models.generate_content')
def test_analyze_json_parse_error(mock_generate_content, client):
    mock_response = MagicMock()
    mock_response.text = "This is not JSON..."
    mock_generate_content.return_value = mock_response

    response = client.post("/analyze", json={"text": "Test error text"})
    
    assert response.status_code == 500
    assert b"AI response was not valid data format" in response.data

@patch('app.client.models.generate_content')
def test_analyze_api_failure(mock_generate_content, client):
    mock_generate_content.side_effect = Exception("API_KEY_INVALID")

    response = client.post("/analyze", json={"text": "Test error block"})
    
    assert response.status_code == 401
    assert b"Invalid API Key" in response.data

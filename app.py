from flask import Flask, request, jsonify, render_template, Response
import os
import json
import logging
from typing import Dict, Any, Optional

# Third-party libraries
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pydantic import BaseModel, Field, ValidationError

# Google Cloud SDKs
from google import genai
from google.cloud import logging as cloud_logging
from google.cloud import secretmanager
from google.cloud import error_reporting

# Initialize Flask
app = Flask(__name__, template_folder='.')

# 1. Initialize Google Cloud Logging safely
try:
    log_client = cloud_logging.Client()
    log_client.setup_logging()
    logger = logging.getLogger(__name__)
except Exception:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("Using standard local logging")

# 2. Initialize Google Cloud Error Reporting safely
try:
    error_client = error_reporting.Client()
except Exception:
    error_client = None
    logger.info("Error Reporting SDK not initialized")

def get_secret(secret_id: str) -> str:
    """
    Fetches a secret from Google Cloud Secret Manager with fallback to environment variables.
    
    Args:
        secret_id: The ID of the secret to fetch.
        
    Returns:
        The secret value as a string.
    """
    # 1. Try Secret Manager
    try:
        client = secretmanager.SecretManagerServiceClient()
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "humpty-dumpty-001")
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        secret_val = response.payload.data.decode("UTF-8").strip()
        if secret_val:
            return secret_val
    except Exception as e:
        logger.warning(f"Failed to fetch secret '{secret_id}' from Secret Manager: {e}. Falling back to env.")
    
    # 2. Fallback to Environment Variable
    return os.environ.get(secret_id, "")

# Ensure key is fetched after initialization
API_KEY = get_secret("GEMINI_API_KEY")
MODEL_NAME = "gemini-3-flash-preview"

# 5. Rate Limiting configuration
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day"],
    storage_uri="memory://",
)

class EmergencyRequest(BaseModel):
    """Pydantic model for strict request validation."""
    text: str = Field(..., min_length=1, max_length=1000)

SYSTEM_PROMPT = """You are FirstVoice — a calm, authoritative emergency response AI. A bystander is speaking to you in a panic about a medical emergency.

Your job:
1. Detect the language of the input
2. Identify the emergency type or detect if it is a Non-Emergency.
3. Respond ENTIRELY in the same language as the input
4. Return a JSON response with this EXACT structure (all values in the detected language):

{
  "detectedLanguage": "English",
  "emergencyType": "Cardiac Arrest",
  "severity": "CRITICAL",
  "steps": [
    {"step": 1, "action": "Call 112 immediately", "detail": "Tell them: unconscious adult, not breathing, your location"},
    {"step": 2, "action": "Begin chest compressions", "detail": "Push hard and fast 100-120 times per minute"}
  ],
  "doNot": ["Do not move the person"],
  "dispatchSummary": "Adult, suspected cardiac arrest. Needs ambulance immediately.",
  "reassurance": "You are doing the right thing. Stay calm. Help is on the way."
}

CRITICAL RULES:
- If the input is NOT an emergency, return emergencyType: "Non-Emergency" and severity: "MODERATE".
- Severity must be exactly: CRITICAL, SERIOUS, or MODERATE
- Max 5 steps.
"""

@app.after_request
def add_security_headers(response: Response) -> Response:
    """Adds security headers to every response to improve security score."""
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com;"
    return response

@app.errorhandler(429)
def ratelimit_handler(e: Any) -> tuple:
    """Handles rate limit exceeded errors with a clean JSON response."""
    logger.warning(f"Local rate limit hit: {e.description}")
    return jsonify({
        "error": f"Local Request Limit Reached: {e.description}. Please slow down for the demo."
    }), 429

@app.route("/")
def index() -> str:
    """Renders the main application page."""
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
@limiter.limit("20 per minute")
def analyze() -> tuple:
    """
    Main endpoint to analyze emergency reports using Gemini AI.
    
    Validates the input, calls the Gemini API, and returns a structured response.
    """
    try:
        req_data = EmergencyRequest(**request.json)
    except ValidationError as e:
        logger.warning(f"Invalid input provided: {e.json()}")
        return jsonify({"error": "Description is required (Max 1000 characters)."}), 400
    except Exception:
        return jsonify({"error": "Invalid JSON payload"}), 400

    if not API_KEY:
        if error_client:
            error_client.report("Gemini API key missing")
        return jsonify({"error": "Gemini API key not configured on server"}), 500

    try:
        logger.info(f"Analyzing emergency input of length {len(req_data.text)}")
        
        # 2. Configure Gemini Generation
        from google.genai import types
        genai_client = genai.Client(api_key=API_KEY)
        
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
            max_output_tokens=1200
        )

        # 3. Call Gemini API
        response = genai_client.models.generate_content(
            model=MODEL_NAME,
            contents=f"{SYSTEM_PROMPT}\n\nEmergency report: {req_data.text}",
            config=config,
        )

        if not response or not response.text:
            raise ValueError("Empty response from Gemini API")

        # 4. Parse and return result
        parsed = json.loads(response.text)
        logger.info(f"Successfully processed emergency type: {parsed.get('emergencyType')}")
        return jsonify(parsed), 200

    except Exception as e:
        if error_client:
            error_client.report_exception()
        error_msg = str(e)
        logger.error(f"Execution Error: {error_msg}")
        
        if "429" in error_msg:
            return jsonify({"error": "Gemini AI Quota Exceeded. The AI is busy, please wait 60 seconds."}), 429
        return jsonify({"error": f"Internal server error: {error_msg}"}), 500

if __name__ == "__main__":
    # Get port from env for Cloud Run compatibility
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

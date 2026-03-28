"""
FirstVoice — Emergency Response API
====================================
A production-grade Flask application that uses Google Gemini AI to analyze
emergency situations and provide structured first-response guidance.

Google Cloud Services Integrated:
- Secret Manager: Secure API key storage
- Cloud Logging: Native GCP log indexing
- Error Reporting: Automated crash tracking
- Firestore: Persistent emergency log database
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from flask import Flask, Response, jsonify, render_template, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pydantic import BaseModel, Field, ValidationError

# ─── Google Cloud SDK Imports ──────────────────────────────────────────────────
from google import genai
from google.genai import types as genai_types
from google.cloud import error_reporting
from google.cloud import firestore as cloud_firestore
from google.cloud import logging as cloud_logging
from google.cloud import secretmanager

# ─── Flask App ─────────────────────────────────────────────────────────────────
app = Flask(__name__, template_folder="templates", static_folder="static")

# ─── 1. Cloud Logging ──────────────────────────────────────────────────────────
try:
    _log_client = cloud_logging.Client()
    _log_client.setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Google Cloud Logging initialized")
except Exception as _e:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.warning("Cloud Logging unavailable, using standard logging: %s", _e)

# ─── 2. Error Reporting ────────────────────────────────────────────────────────
try:
    error_client: error_reporting.Client | None = error_reporting.Client()
    logger.info("Google Cloud Error Reporting initialized")
except Exception as _e:
    error_client = None
    logger.warning("Error Reporting unavailable: %s", _e)

# ─── 3. Firestore ──────────────────────────────────────────────────────────────
try:
    db: cloud_firestore.Client | None = cloud_firestore.Client()
    logger.info("Google Cloud Firestore initialized")
except Exception as _e:
    db = None
    logger.warning("Firestore unavailable: %s", _e)


# ─── Secret Manager Helper ─────────────────────────────────────────────────────
def get_secret(secret_id: str) -> str:
    """Fetch a secret from Google Cloud Secret Manager with env-var fallback.

    Args:
        secret_id: The name of the secret in Secret Manager.

    Returns:
        The decoded secret string, or empty string if unavailable.
    """
    try:
        client = secretmanager.SecretManagerServiceClient()
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        if project_id:
            name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            value = response.payload.data.decode("UTF-8").strip()
            if value:
                logger.info("Secret '%s' successfully fetched from Secret Manager", secret_id)
                return value
    except Exception as exc:
        logger.warning(
            "Failed to fetch secret '%s' from Secret Manager: %s. Using env fallback.",
            secret_id,
            exc,
        )
    return os.environ.get(secret_id, "")


# ─── App Configuration ─────────────────────────────────────────────────────────
API_KEY: str = get_secret("GEMINI_API_KEY")
MODEL_NAME: str = "gemini-2.0-flash"

# ─── Gemini Client (module-level singleton for efficiency) ─────────────────────
genai_client: genai.Client | None = genai.Client(api_key=API_KEY) if API_KEY else None

# ─── Rate Limiter ──────────────────────────────────────────────────────────────
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day"],
    storage_uri="memory://",
)

# ─── Pydantic Input Model ──────────────────────────────────────────────────────
class EmergencyRequest(BaseModel):
    """Validates and enforces constraints on incoming emergency report payloads."""

    text: str = Field(..., min_length=1, max_length=1000,
                      description="Natural language description of the emergency situation.")


# ─── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are FirstVoice — a calm, authoritative emergency response AI.
A bystander is speaking to you in a panic about a medical emergency.

Your job:
1. Detect the language of the input
2. Identify the emergency type (or "Non-Emergency" if not urgent)
3. Respond ENTIRELY in the same language as the input
4. Return a JSON response with this EXACT structure:

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
- Non-emergency input: emergencyType = "Non-Emergency", severity = "MODERATE"
- Severity must be exactly one of: CRITICAL, SERIOUS, MODERATE
- Maximum 5 steps
"""


# ─── Firestore Logger ──────────────────────────────────────────────────────────
def log_emergency_to_firestore(input_text: str, result: dict[str, Any]) -> None:
    """Persist an emergency analysis event to Google Cloud Firestore.

    Args:
        input_text: The raw emergency description from the user.
        result: The structured AI response dict.
    """
    if db is None:
        return
    try:
        doc = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "inputText": input_text,
            "emergencyType": result.get("emergencyType", "Unknown"),
            "severity": result.get("severity", "Unknown"),
            "detectedLanguage": result.get("detectedLanguage", "Unknown"),
        }
        db.collection("emergencies").add(doc)
        logger.info("Emergency event logged to Firestore: %s", result.get("emergencyType"))
    except Exception as exc:
        logger.warning("Firestore write failed: %s", exc)


# ─── Security Headers Middleware ───────────────────────────────────────────────
@app.after_request
def add_security_headers(response: Response) -> Response:
    """Attach strict security headers to every HTTP response.

    Args:
        response: The Flask response object.

    Returns:
        The response object with security headers added.
    """
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com;"
    )
    return response


# ─── Rate Limit Handler ────────────────────────────────────────────────────────
@app.errorhandler(500)
def internal_error_handler(exc: Any) -> tuple[Response, int]:
    """Return JSON for all 500 errors — prevents Cloud Run from serving HTML error pages.

    Args:
        exc: The exception that triggered the 500.

    Returns:
        A JSON response with status 500.
    """
    logger.error("Internal server error: %s", exc)
    if error_client:
        error_client.report_exception()
    return jsonify({"error": "An internal server error occurred. Please try again."}), 500


@app.errorhandler(404)
def not_found_handler(exc: Any) -> tuple[Response, int]:
    """Return JSON for 404 errors.

    Args:
        exc: The exception that triggered the 404.

    Returns:
        A JSON response with status 404.
    """
    return jsonify({"error": "Endpoint not found."}), 404


@app.errorhandler(429)
def ratelimit_handler(exc: Any) -> tuple[Response, int]:
    """Return a structured JSON error for rate-limited requests.

    Args:
        exc: The rate limit exception raised by Flask-Limiter.

    Returns:
        A JSON response with status 429.
    """
    logger.warning("Rate limit exceeded: %s", exc.description)
    return jsonify({"error": f"Too many requests: {exc.description}. Please slow down."}), 429


# ─── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index() -> str:
    """Render the main FirstVoice application page.

    Returns:
        Rendered HTML string of the main page.
    """
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
@limiter.limit("20 per minute")
def analyze() -> tuple[Response, int]:
    """Analyze an emergency description using Gemini AI and return structured guidance.

    Validates the request with Pydantic, calls the Gemini model, logs the result
    to Firestore, and returns JSON-formatted emergency response steps.

    Returns:
        A tuple of (JSON response, HTTP status code).
    """
    # ── Validate input ─────────────────────────────────────────────
    try:
        req_data = EmergencyRequest(**request.json)
    except ValidationError as exc:
        logger.warning("Input validation failed: %s", exc.json())
        return jsonify({"error": "Description is required (Max 1000 characters)."}), 400
    except Exception:
        return jsonify({"error": "Invalid JSON payload"}), 400


    if not genai_client:
        return jsonify({"error": "Gemini API key not configured on server"}), 500

    # ── Call Gemini AI ─────────────────────────────────────────────
    try:
        logger.info("Analyzing emergency input (%d chars)", len(req_data.text))

        config = genai_types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
            max_output_tokens=1200,
        )
        response = genai_client.models.generate_content(
            model=MODEL_NAME,
            contents=f"{SYSTEM_PROMPT}\n\nEmergency report: {req_data.text}",
            config=config,
        )

        if not response or not response.text:
            raise ValueError("Empty response received from Gemini API")

        parsed: dict[str, Any] = json.loads(response.text)
        logger.info("Successfully triage: %s (%s)", parsed.get("emergencyType"), parsed.get("severity"))

        # ── Log to Firestore ───────────────────────────────────────
        log_emergency_to_firestore(req_data.text, parsed)

        return jsonify(parsed), 200

    except Exception as exc:
        if error_client:
            error_client.report_exception()
        error_msg = str(exc)
        logger.error("Gemini API error: %s", error_msg)

        if "429" in error_msg:
            return jsonify({"error": "Gemini AI quota exceeded. Please wait 60 seconds and try again."}), 429
        return jsonify({"error": f"Internal server error: {error_msg}"}), 500


# ─── Entrypoint ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)

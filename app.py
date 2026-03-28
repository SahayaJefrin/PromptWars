from flask import Flask, request, jsonify, render_template
import os
import json
import logging
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from google import genai
from google.genai import types

# Setup Google Cloud Structured Logging
class GCPStructuredFormatter(logging.Formatter):
    def format(self, record):
        # Map python log levels to GCP severity
        severity_map = {
            "DEBUG": "DEBUG",
            "INFO": "INFO",
            "WARNING": "WARNING",
            "ERROR": "ERROR",
            "CRITICAL": "CRITICAL",
        }
        log_entry = {
            "severity": severity_map.get(record.levelname, "INFO"),
            "message": record.getMessage(),
            "logger": record.name,
        }
        if record.exc_info:
            log_entry["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_entry)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setFormatter(GCPStructuredFormatter())
if not logger.handlers:
    logger.addHandler(ch)

app = Flask(__name__, template_folder='.')

# Rate Limiting configuration to prevent abuse
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day"],
    storage_uri="memory://",
)

# Initialize GenAI Client using environment variable
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
# Updated to Google AI Studio's gemini-3-flash-preview with thinking & search logic
MODEL_NAME = "gemini-3-flash-preview"

SYSTEM_PROMPT = """You are FirstVoice — a calm, authoritative emergency response AI. A bystander is speaking to you in a panic about a medical emergency.

Your job:
1. Detect the language of the input
2. Identify the emergency type (cardiac arrest, seizure, stroke, choking, fall/fracture, drowning, etc.) or detect if it is a Non-Emergency.
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
- If the input is NOT an emergency (e.g., "Hello", "How are you"), return emergencyType: "Non-Emergency" and severity: "MODERATE".
- Severity must be exactly: CRITICAL, SERIOUS, or MODERATE
- Max 5 steps. Be concise. Panicked people cannot read long text.
- ALL text values must be in the SAME language as the user's input
"""

@app.after_request
def add_security_headers(response):
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com;"
    return response

@app.route("/")
def index():
    return render_template("index.html")

@app.errorhandler(429)
def ratelimit_handler(e):
    logger.warning(f"Local rate limit hit: {e.description}")
    return jsonify({"error": f"Local Request Limit Reached: {e.description}. Please slow down for the demo."}), 429

@app.route("/analyze", methods=["POST"])
@limiter.limit("20 per minute")
def analyze():
    if not os.getenv("GEMINI_API_KEY"):
        logger.error("Gemini API key not configured on server")
        return jsonify({"error": "Gemini API key not configured on server"}), 500

    data = request.json
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400
        
    text = data.get("text", "").strip()

    if not text:
        logger.warning("Empty emergency description provided.")
        return jsonify({"error": "Emergency description is required"}), 400
        
    if len(text) > 1000:
        logger.warning(f"Payload too large: {len(text)} chars")
        return jsonify({"error": "Description is too long. Please keep it under 1000 characters."}), 400

    try:
        logger.info(f"Analyzing emergency input of length {len(text)}")
        generate_content_config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,  # Keep low for structured output
            max_output_tokens=1200,
            thinking_config=types.ThinkingConfig(
                thinking_level="HIGH",
            ),
            tools=[types.Tool(googleSearch=types.GoogleSearch())]
        )

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=SYSTEM_PROMPT + "\n\nEmergency report from bystander: " + text,
            config=generate_content_config,
        )

        if not response or not response.text:
            logger.error("No response from AI model")
            return jsonify({"error": "No response from AI. Try again."}), 500

        # Native JSON parsing, no regex needed due to response_mime_type="application/json"
        parsed = json.loads(response.text)
        logger.info(f"Successfully processed emergency type: {parsed.get('emergencyType')}")
        return jsonify(parsed)

    except json.JSONDecodeError as decode_err:
        logger.error(f"Failed to parse JSON response: {decode_err}")
        return jsonify({"error": "AI response was not valid data format."}), 500
    except Exception as e:
        error_msg = str(e)
        logger.error(f"API Error: {error_msg}")
        if "API_KEY_INVALID" in error_msg:
            return jsonify({"error": "Invalid API Key"}), 401
        if "429" in error_msg:
            return jsonify({"error": "Gemini AI Quota Exceeded. The AI is busy, please wait 60 seconds."}), 429
        return jsonify({"error": error_msg}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)


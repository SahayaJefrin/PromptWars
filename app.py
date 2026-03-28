from flask import Flask, request, jsonify, render_template
import os
import json
import re
from google import genai
from google.genai import types

app = Flask(__name__, template_folder='.')

# Initialize GenAI Client using environment variable
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_NAME = "gemini-3-flash-preview"

SYSTEM_PROMPT = """You are FirstVoice — a calm, authoritative emergency response AI. A bystander is speaking to you in a panic about a medical emergency happening right now.

Your job:
1. Detect the language of the input
2. Identify the emergency type (cardiac arrest, seizure, stroke, choking, fall/fracture, drowning, etc.)
3. Respond ENTIRELY in the same language as the input
4. Return a JSON response with this EXACT structure (all values in the detected language):

{
  "detectedLanguage": "English",
  "emergencyType": "Cardiac Arrest",
  "severity": "CRITICAL",
  "steps": [
    {"step": 1, "action": "Call 112 immediately", "detail": "Tell them: unconscious adult, not breathing, your location"},
    {"step": 2, "action": "Begin chest compressions", "detail": "Place heel of hand on center of chest. Push hard and fast 100-120 times per minute"},
    {"step": 3, "action": "Give rescue breaths", "detail": "Tilt head back, lift chin, give 2 breaths after every 30 compressions"},
    {"step": 4, "action": "Do not stop until help arrives", "detail": "Keep going. You are keeping them alive."}
  ],
  "doNot": ["Do not move the person", "Do not give water or food"],
  "dispatchSummary": "Adult, suspected cardiac arrest, bystander performing CPR. Needs ambulance immediately.",
  "reassurance": "You are doing the right thing. Stay calm and keep going. Help is on the way."
}

CRITICAL RULES:
- Severity must be exactly: CRITICAL, SERIOUS, or MODERATE
- Max 5 steps. Be concise. Panicked people cannot read long text.
- ALL text values (action, detail, doNot, dispatchSummary, reassurance, emergencyType) must be in the SAME language as the user's input
- Only return valid JSON. No markdown, no explanation, no code blocks.
"""

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    # Ensure api_key is configured (though client is initialized above)
    if not os.getenv("GEMINI_API_KEY"):
        return jsonify({"error": "Gemini API key not configured on server"}), 500

    data = request.json
    text = data.get("text", "").strip()

    if not text:
        return jsonify({"error": "Emergency description is required"}), 400

    try:
        # Configure tools and thinking based on reference
        generate_content_config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_level="HIGH",
            ),
            tools=[types.Tool(googleSearch=types.GoogleSearch())],
            temperature=0.1,  # Keep low for structured output
            max_output_tokens=1200
        )

        # Generate content using the new SDK
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=SYSTEM_PROMPT + "\n\nEmergency report from bystander: " + text,
            config=generate_content_config,
        )

        if not response or not response.text:
            return jsonify({"error": "No response from AI. Try again."}), 500

        raw = response.text
        # Strip markdown code fences if present (Gemini often wraps JSON)
        clean = re.sub(r"```json|```", "", raw).strip()
        parsed = json.loads(clean)
        return jsonify(parsed)

    except Exception as e:
        # Handle API or parsing errors
        error_msg = str(e)
        if "API_KEY_INVALID" in error_msg:
            return jsonify({"error": "Invalid API Key"}), 401
        return jsonify({"error": error_msg}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(debug=True, host="0.0.0.0", port=port)

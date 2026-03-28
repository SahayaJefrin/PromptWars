from flask import Flask, request, jsonify, render_template
import requests
import os
import json
import re

app = Flask(__name__)

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

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
    data = request.json
    api_key = data.get("apiKey", "").strip()
    text = data.get("text", "").strip()

    if not api_key:
        return jsonify({"error": "API key is required"}), 400
    if not text:
        return jsonify({"error": "Emergency description is required"}), 400

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": SYSTEM_PROMPT + "\n\nEmergency report from bystander: " + text}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 1200
        }
    }

    try:
        resp = requests.post(
            f"{GEMINI_URL}?key={api_key}",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=15
        )
        resp.raise_for_status()
        gemini_data = resp.json()

        raw = gemini_data["candidates"][0]["content"]["parts"][0]["text"]
        # Strip markdown code fences if present
        clean = re.sub(r"```json|```", "", raw).strip()
        parsed = json.loads(clean)
        return jsonify(parsed)

    except requests.exceptions.Timeout:
        return jsonify({"error": "Request timed out. Please try again."}), 504
    except requests.exceptions.HTTPError as e:
        return jsonify({"error": f"Gemini API error: {e.response.status_code}"}), 502
    except (json.JSONDecodeError, KeyError) as e:
        return jsonify({"error": "Failed to parse response. Try again."}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

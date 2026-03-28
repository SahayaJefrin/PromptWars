# 🫀 FirstVoice — Emergency Response AI
### PromptWars 2026 | Built with Gemini 3.1 Flash

> **You panic. It doesn't.**

FirstVoice turns panicked voice/text into calm, structured, life-saving action plans — instantly. Powered by **Gemini 3 Flash**, it provides real-time first-aid guidance in 6 Indian languages.

---

## 🚀 Key Features (Hackathon Ready)
- **🧠 Enhanced Reasoning**: Powered by `gemini-3-flash-preview` with **Thinking Mode** enabled for accurate emergency triage.
- **🔍 Real-time Grounding**: Integrated with **Google Search** tools to ensure the most up-to-date and accurate emergency protocols.
- **🛡️ Security & Scalability**: 
  - **Rate Limiting**: Protected by `Flask-Limiter` to prevent API abuse.
  - **Secure Headers**: Implements CSP, X-Frame-Options, and XSS protection.
  - **Input Validation**: Strict payload sanitization for emergency reports.
- **♿ Accessibility**: Built with semantic HTML, **ARIA-Live** status announcements, and screen-reader optimized elements.
- **🌐 6 Indian Languages**: Support for Hindi, Kannada, Tamil, Telugu, Marathi, and English.
- **⚡ Cloud Managed**: Deployed on **Google Cloud Run** with Continuous Deployment via GitHub Actions.

---

## 🏗 Architecture
```
User Interface (Mobile/Desktop)
     │
     │ 🗣 Voice (Web Speech API)
     ▼
Flask Application (deployed on Cloud Run)
     │
     │ 🛡 Rate Limiter & Security Layers
     │ 📡 POST /analyze
     ▼
Gemini 3 Flash API (Google AI Studio)
     │
     │ 🧠 Thinking Core + 🔍 Google Search
     ▼
Structured JSON ➔ 🔊 Natural TTS + 📜 Visual Plan
```

---

## 🎯 Demo Script for Judges
1. Switch language to **हिंदी** (Hindi).
2. Press 🎙 and say: *"मेरे पापा गिर गए, सांस नहीं ले रहे, होंठ नीले हो रहे हैं"* (My father collapsed, he's not breathing, lips are turning blue).
3. Watch it identify **Cardiac Arrest** and utilize **Gemini Thinking** to generate a step-by-step CPR guide.
4. Press 🔊 — it reads the steps aloud in Hindi with perfect urgency.

---

## ✅ Quality & Robustness
- **Testing**: Automated `pytest` suite with mocked SDK responses for reliability.
- **Logging**: Integrated **Google Cloud Structured Logging** (JSON) for seamless Operations Suite monitoring.
- **Containerization**: Optimized Docker build for instant Cloud Run scaling.

---

## 🚀 Setup & Development

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the server
python app.py

# 3. Run Automated Tests
pytest tests/test_app.py
```

---

## ⚠️ Disclaimer
This app is for research and demonstration purposes. It assists bystanders — it does NOT replace emergency services.
**Always call 112 first.**

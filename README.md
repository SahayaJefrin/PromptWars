# 🫀 FirstVoice — Emergency Response AI
### PromptWars 2026 | Built with Gemini

> **You panic. It doesn't.**

FirstVoice turns panicked voice/text into calm, structured, life-saving action plans — instantly. Supports 6 Indian languages.

---

## 🚀 Setup (2 minutes)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the server
python app.py

# 3. Open in browser (or phone on same WiFi)
http://localhost:5000
```

## 📱 Demo on Mobile
On the same WiFi network, open:
```
http://<your-laptop-ip>:5000
```
Find your IP: `ipconfig` (Windows) or `ifconfig` (Mac/Linux)

---

## 🔑 Gemini API Key
Get one free at: https://aistudio.google.com/app/apikey

---

## 🌐 Languages Supported
| Language | Voice Input | AI Response |
|----------|-------------|-------------|
| English  | ✅          | ✅          |
| हिंदी    | ✅          | ✅          |
| ಕನ್ನಡ   | ✅          | ✅          |
| தமிழ்   | ✅          | ✅          |
| తెలుగు  | ✅          | ✅          |
| मराठी   | ✅          | ✅          |

---

## 🏗 Architecture
```
Mobile Browser
     │
     │ Voice (Web Speech API)
     ▼
Flask Server (app.py)
     │
     │ POST /analyze
     ▼
Gemini 2.0 Flash API
     │
     ▼
Structured JSON → UI + TTS
```

---

## 🎯 Demo Script for Judges
1. Switch language to **हिंदी**
2. Press 🎙 and say: *"मेरे पापा गिर गए, सांस नहीं ले रहे, होंठ नीले हो रहे हैं"*
3. Watch it identify **Cardiac Arrest** and respond in Hindi
4. Press 🔊 — it reads the steps aloud in Hindi

---

## ⚠️ Disclaimer
This app assists bystanders — it does NOT replace emergency services.
**Always call 112 first.**

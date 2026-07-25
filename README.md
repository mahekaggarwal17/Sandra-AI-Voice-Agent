# 🎙️ Sandra AI — Real-Time Voice Assistant & Autonomous Agent Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://www.python.org/)
[![Gemini Live API](https://img.shields.io/badge/AI-Gemini%20Live%20API%20%2F%20NVIDIA%20NIM-orange.svg)](https://ai.google.dev/)
[![Google Calendar](https://img.shields.io/badge/Integration-Google%20Calendar%20%26%20Gmail-red.svg)](https://developers.google.com/)

> **Sandra AI** is an ultra-low latency, real-time conversational AI voice assistant. Built with bidirectional WebSocket streaming, smart Google Calendar event scheduling, Google Meet link generation, automated email delivery, and persistent SQLite memory.

---

## ✨ Key Features

### 🎙️ 1. Real-Time Ultra-Low Latency Voice Agent
- **Bidirectional Audio Streaming**: Powered by **Gemini 2.0 Live API** (`BidiGenerateContent` WebSocket protocol) and **NVIDIA NIM** LLMs for natural human conversation.
- **Barge-In & Active Interruption**: Micro-second response latency with active user speech interruption support.
- **Wake-Word Listener**: Hands-free voice activation when you say *"Hey Sandra"*, *"Hi Sandra"*, or *"Hello Sandra"*.

### 📅 2. Smart Calendar & Google Meet Booking
- **Flexible Datetime Parser**: Seamlessly understands phrases like *"tomorrow at 3 PM"*, *"next Monday at 10 AM"*, *"today at 5 PM"*, or ISO dates.
- **Google Meet Integration**: Automatically generates and attaches active Google Meet video links to booked calendar events.
- **Conflict Prevention**: Automatically checks for double-bookings and suggests alternate free slots.
- **Local SQLite Fallback**: Full local database calendar fallback (`local_meetings`) ensures scheduling works 100% reliably even when offline or unauthenticated.

### ✉️ 3. Real Email Delivery & Call Summaries
- **Gmail API & SMTP Fallback**: Sends meeting confirmations and notifications directly to recipients. Automatically falls back to standard SMTP email delivery if Gmail OAuth is unauthenticated.
- **Post-Call Summaries**: Automatically logs conversation transcripts and emails a beautifully formatted HTML summary after every voice call.

### 💾 4. Memory & Profile Context
- **SQLite Memory Manager**: Remembers user preferences, names, contact details, and past task instructions across sessions.
- **Session History Drawer**: Inspect, review, and replay past call transcripts anytime from the dashboard.

### 🎨 5. Glassmorphic Web UI Dashboard
- **Interactive Visualizer Orb**: Real-time canvas audio waveform visualizer responding to mic input and agent speech.
- **Live Captions**: Subtitle caption bar with active voice role indicators ("You" vs "Sandra").
- **Multi-Device Support**: Hardware microphone selector, Web Speech SR, and custom voice config.

### 📞 6. Outbound Telephony Fallback
- **Twilio Integration**: Placed telephony call fallback to trigger phone calls directly to user mobile phones when out of browser range.

---

## 🗺️ System Architecture

```text
               ┌─────────────────────────────────────────┐
               │    🌐 Glassmorphic Frontend UI          │
               │   (Port 5000 / Web Audio PCM / WSS)     │
               └────────────────────┬────────────────────┘
                                    │
                                    ▼
               ┌─────────────────────────────────────────┐
               │    🐍 Unified Python Gateway            │
               │   (api_server.py - Flask + WebSockets)  │
               └────────┬───────────────────────┬────────┘
                        │                       │
         ┌──────────────┴──────────────┐ ┌──────┴──────────────────────┐
         ▼                             ▼ ▼                             ▼
┌───────────────────┐       ┌────────────────────┐          ┌───────────────────┐
│ 🤖 Gemini Live /  │       │ 📅 Google Calendar │          │  ✉️ Gmail API /   │
│   NVIDIA NIM WSS  │       │   (Meet & Events)  │          │   SMTP Fallback   │
└───────────────────┘       └────────────────────┘          └───────────────────┘
                                       │                              │
                                       ▼                              ▼
                            ┌────────────────────┐          ┌───────────────────┐
                            │ 💾 SQLite Database │          │ 📞 Twilio Voice   │
                            │   (memory.db)      │          │     Telephony     │
                            └────────────────────┘          └───────────────────┘
```

---

## 📂 Project Structure

```text
.
├── api_server.py        # Core Flask & WebSocket Proxy server (Ports 5000 & 5001)
├── calendar_tool.py     # Calendar scheduling, date parsing, Gmail API & SMTP email logic
├── database.py          # SQLite database schema, user auth, OAuth tokens & profile memory
├── notifications.py     # SMTP email builder & Twilio outbound telephony integration
├── memory_manager.py    # Memory retrieval and profile context engine
├── build_ui.py          # Dashboard UI builder & layout generator
├── index.html           # Production Web Dashboard UI with WebRTC/WSS audio processing
├── pcm-processor.js     # Web Audio API worklet for 16kHz PCM audio streaming
├── assets/              # Avatar images & visual design assets
├── .gitignore           # Git ignore rules for DB, environment variables & tokens
└── requirements.txt     # Python project dependencies
```

---

## ⚡ Quick Start & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/mahekaggarwal17/Sandra-AI-Voice-Agent.git
cd Sandra-AI-Voice-Agent
```

### 2. Create Virtual Environment & Install Dependencies

**Windows:**
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

---

## 🔑 Environment Configuration (`.env`)

Create a `.env` file in the root directory:

```ini
# Flask & App Credentials
FLASK_SECRET_KEY=sandras-super-secret-key-998877

# Google OAuth Credentials (Optional for Google Sync)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_API_REDIRECT_URI=http://localhost:5000/auth/callback
HOST_EMAIL=mahek.aggarwal17@gmail.com
HOST_CALENDAR_ID=primary

# SMTP Email Credentials (For Email Notifications)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# Twilio Credentials (Optional for Telephony Call Fallback)
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# AI Keys (Alternative to entering in UI)
GEMINI_API_KEY=your_gemini_api_key
NVIDIA_API_KEY=your_nvidia_api_key
```

---

## 🚀 Running Sandra AI

Start the unified HTTP API & WebSocket Proxy server:

```bash
python api_server.py
```

1. Open your web browser and navigate to: **`http://localhost:5000`**
2. **Log In** or **Register** a local user account.
3. Enter your **Gemini API Key** (or NVIDIA NIM API key).
4. Click **Start Session** (or say *"Hey Sandra"*!)
5. Speak naturally with Sandra:
   - *"Check my schedule for tomorrow at 3 PM."*
   - *"Book a meeting with John tomorrow at 4 PM to discuss project roadmap."*
   - *"Send an email to me with meeting notes."*
   - *"Remember that my favorite coffee is Cappuccino."*

---

## 🧪 Testing & Verification

Check Python syntax and compile validity across all modules:

```bash
python -m py_compile api_server.py database.py calendar_tool.py notifications.py
```

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).

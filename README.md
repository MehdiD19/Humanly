# Humanly

A real-time voice chat application with LiveKit and AI agents, featuring intelligent human escalation detection.

## Prerequisites

- Node.js (for Frontend)
- Python 3.11+ (for Backend)
- LiveKit Server (local or cloud)
- API keys: Deepgram, ElevenLabs

## Setup

### Backend Setup

1. **Install dependencies:**
   ```bash
   cd Backend
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   Create `.env` in `Backend/`:
   ```env
   LIVEKIT_URL=ws://localhost:7880
   LIVEKIT_API_KEY=your_livekit_api_key
   LIVEKIT_API_SECRET=your_livekit_api_secret
   DEEPGRAM_API_KEY=your_deepgram_api_key
   ELEVENLABS_API_KEY=your_elevenlabs_api_key
   ```

3. **Run two processes:**
   ```bash
   # Terminal 1: API Server
   cd Backend
   python api_server.py
   
   # Terminal 2: LiveKit Agent
   cd Backend
   python simple_agent.py start
   ```

### Frontend Setup

1. **Install dependencies:**
   ```bash
   cd Frontend
   npm install
   ```

2. **Configure environment variables:**
   Create `.env` in `Frontend/`:
   ```env
   VITE_BACKEND_URL=http://localhost:8000
   VITE_LIVEKIT_URL=ws://localhost:7880
   ```

3. **Run development server:**
   ```bash
   npm run dev
   ```
   Access at `http://localhost:5173` (or port shown in terminal)

## Features

### 🚨 Human Escalation Detection
The agent now includes intelligent detection for moments requiring human intervention:
- **Financial decisions** (offers, payments, contracts)
- **Authorization requests** (approvals, sensitive actions)
- **Information gaps** (questions outside agent's knowledge)
- **Sensitive topics** (medical, legal matters)
- **Direct user requests** for human assistance

All escalations are:
- ✅ Logged in real-time with detailed context
- ✅ Saved to `Backend/escalations.json` for review
- ✅ Categorized by urgency (low/medium/high/critical) and type
- ✅ Include recent conversation transcript

**[📖 Read the Escalation Detection Guide](Backend/ESCALATION_DETECTION.md)**

## Running the Application

1. Start the backend (API Server + LiveKit Agent in separate terminals)
2. Start the frontend
3. Open the application in your browser
4. Use the voice or text chat interface to interact with the AI agent

## Testing Escalation Detection

Try these phrases to test the escalation system:
- "Do you think I should accept the 10,000 euro offer?"
- "Can you approve this purchase for me?"
- "I need to speak with a human"

See **[Test Scenarios](Backend/test_escalation_scenarios.md)** for comprehensive testing examples.

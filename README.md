# Humanly

A real-time voice chat application with LiveKit and AI agents.

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

## Running the Application

1. Start the backend (API Server + LiveKit Agent in separate terminals)
2. Start the frontend
3. Open the application in your browser
4. Use the voice or text chat interface to interact with the AI agent

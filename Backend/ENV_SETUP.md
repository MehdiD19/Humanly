# Backend Environment Setup

## Required Environment Variables

Create a `.env` file in the `Backend/` directory with the following variables:

```env
# LiveKit Server Configuration
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=your_livekit_api_key_here
LIVEKIT_API_SECRET=your_livekit_api_secret_here

# Google_API_KEY=your_google_api_key_here

# Deepgram API (for Speech-to-Text)
DEEPGRAM_API_KEY=your_deepgram_api_key_here

# Eleven Labs API (for Text-to-Speech)
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
```

## Getting LiveKit Credentials

### Option 1: Local LiveKit Server
1. Download LiveKit server from https://livekit.io/
2. Run it locally
3. Get API credentials from the server configuration

### Option 2: LiveKit Cloud
1. Sign up at https://cloud.livekit.io/
2. Create a project
3. Copy the API Key, API Secret, and WebSocket URL from your project settings

## Running the Backend

You need to run TWO separate processes:

### 1. API Server (Port 8000)
```bash
cd Backend
python api_server.py
```

This serves the token generation endpoint for the frontend.

### 2. LiveKit Agent
```bash
cd Backend
python simple_agent.py start
```

This is the AI agent that handles conversations in LiveKit rooms.


# Frontend Environment Setup

## Required Environment Variables

Create a `.env` file in the `Frontend/` directory with the following variables:

```env
# Backend API URL (where token generation happens)
VITE_BACKEND_URL=http://localhost:8000

# LiveKit WebSocket URL (where real-time communication happens)
VITE_LIVEKIT_URL=ws://localhost:7880
```

## What These Variables Do

### VITE_BACKEND_URL
- **Purpose**: The URL of your backend API server that generates LiveKit access tokens
- **Default**: `http://localhost:8000`
- **When to change**: If your API server runs on a different port or domain

### VITE_LIVEKIT_URL
- **Purpose**: The WebSocket URL of your LiveKit server for real-time audio/video communication
- **Default**: `ws://localhost:7880`
- **When to change**: 
  - If using LiveKit Cloud, set this to your cloud WebSocket URL (e.g., `wss://your-project.livekit.cloud`)
  - If running LiveKit locally on a different port

## Example Configurations

### Local Development
```env
VITE_BACKEND_URL=http://localhost:8000
VITE_LIVEKIT_URL=ws://localhost:7880
```

### Production (LiveKit Cloud)
```env
VITE_BACKEND_URL=https://your-api-domain.com
VITE_LIVEKIT_URL=wss://your-project.livekit.cloud
```

## Running the Frontend

```bash
cd Frontend
npm install
npm run dev
```

The frontend will run on `http://localhost:3000` (or the port shown in terminal).



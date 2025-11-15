# Escalation System Setup Guide

This guide explains how to use the real-time escalation system with WebSocket support.

## Architecture

- **Backend API** (`api_server.py`): FastAPI server with WebSocket endpoints
- **Agent** (`simple_agent.py`): Sends escalations and receives responses via WebSocket
- **Frontend Dashboard**: React component for operators to view and respond to escalations

## Setup

### 1. Backend Dependencies

Make sure you have the required Python packages:

```bash
pip install httpx websockets
```

### 2. Environment Variables

Add to your `.env` file:

```env
API_BASE_URL=http://localhost:8000
```

### 3. Start the Backend API Server

```bash
cd Backend
python api_server.py
```

The API server will run on `http://localhost:8000`

### 4. Start the Agent

In a separate terminal:

```bash
cd Backend
python simple_agent.py dev
```

### 5. Start the Frontend Dashboard

In another terminal:

```bash
cd Frontend
npm run dev
```

Then open: `http://localhost:5173?mode=dashboard`

## How It Works

### Flow

1. **Agent detects escalation** → Calls `escalate_to_human()` function
2. **Agent sends HTTP POST** → `/api/escalations` with escalation details
3. **Backend stores escalation** → In-memory storage (for development)
4. **Backend broadcasts** → WebSocket message to all connected frontend clients
5. **Frontend receives** → Shows new escalation in dashboard
6. **Operator responds** → Types response and submits
7. **Backend receives response** → Stores it and sends via WebSocket to agent
8. **Agent receives response** → Injects it into conversation using `session.generate_reply()`

### API Endpoints

- `POST /api/escalations` - Create new escalation (called by agent)
- `GET /api/escalations/pending` - Get all pending escalations (called by frontend)
- `GET /api/escalations/{id}` - Get specific escalation details
- `POST /api/escalations/{id}/respond` - Submit human response

### WebSocket Endpoints

- `ws://localhost:8000/ws/agent/{escalation_id}` - Agent connects to receive responses
- `ws://localhost:8000/ws/frontend` - Frontend connects to receive escalation updates

## Testing

1. Start the backend API server
2. Start the agent
3. Open the frontend dashboard (`?mode=dashboard`)
4. Start a conversation with the agent
5. Trigger an escalation by asking something like: "Should I accept this 10,000 euro offer?"
6. The escalation should appear in the dashboard
7. Type a response and submit
8. The agent should receive the response and incorporate it into the conversation

## Notes

- **In-memory storage**: Escalations are stored in memory and will be lost on server restart
- **WebSocket reconnection**: Frontend automatically reconnects if connection is lost
- **Real-time updates**: All escalations are pushed in real-time via WebSocket
- **Multiple operators**: Multiple frontend clients can connect simultaneously

## Production Considerations

For production, consider:

1. **Database storage**: Replace in-memory storage with PostgreSQL/MongoDB
2. **Authentication**: Add authentication for operators
3. **Rate limiting**: Add rate limiting to API endpoints
4. **Error handling**: Enhanced error handling and retry logic
5. **Monitoring**: Add logging and monitoring for escalations
6. **Scalability**: Use Redis for WebSocket connection management in multi-server setups


#!/usr/bin/env python3

import os
import logging
import json
import uuid
import asyncio
from datetime import timedelta, datetime
from pathlib import Path
from typing import Dict, Set, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from livekit import api
from anthropic import Anthropic

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api-server")

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# Initialize FastAPI
app = FastAPI(title="LiveKit Token API")

# Configure CORS to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Vite dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for escalations
escalations: Dict[str, dict] = {}
agent_websockets: Dict[str, WebSocket] = {}  # escalation_id -> websocket
frontend_websockets: Set[WebSocket] = set()  # All frontend connections

# Initialize Anthropic Claude client (after loading env vars)
claude_client = None
claude_api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
if claude_api_key:
    try:
        claude_client = Anthropic(api_key=claude_api_key)
        logger.info("✅ Claude API client initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Claude client: {e}")
        claude_client = None
else:
    logger.warning("⚠️ ANTHROPIC_API_KEY or CLAUDE_API_KEY not set - insights generation will be disabled")

# Request/Response models
class TokenRequest(BaseModel):
    room_name: str
    participant_name: str
    user_id: str | None = None

class TokenResponse(BaseModel):
    token: str
    url: str

class EscalationRequest(BaseModel):
    room_name: str
    user_id: str
    reason: str
    urgency: str
    decision_type: str
    context_details: str = ""
    recent_transcript: list = []

class EscalationResponse(BaseModel):
    escalation_id: str
    status: str

class HumanResponseRequest(BaseModel):
    response_text: str

async def generate_decision_insights(escalation: dict) -> Optional[str]:
    """Generate AI insights about the escalation decision using Claude."""
    escalation_id = escalation.get("escalation_id", "unknown")
    logger.info(f"🔍 [INSIGHTS] Starting insight generation for escalation {escalation_id}")
    
    if not claude_client:
        logger.warning(f"⚠️ [INSIGHTS] Claude client not initialized - skipping insights for {escalation_id}")
        return None
    
    try:
        # Build context from escalation
        reason = escalation.get("reason", "")
        decision_type = escalation.get("decision_type", "")
        context_details = escalation.get("context_details", "")
        urgency = escalation.get("urgency", "")
        
        logger.info(f"📋 [INSIGHTS] Escalation context - Type: {decision_type}, Urgency: {urgency}, Reason length: {len(reason)} chars")
        
        # Build conversation context
        transcript = escalation.get("recent_transcript", [])
        conversation_context = ""
        if transcript:
            conversation_context = "\n".join([
                f"{msg.get('role', 'user').title()}: {msg.get('content', '')}"
                for msg in transcript[-5:]  # Last 5 messages
            ])
            logger.info(f"💬 [INSIGHTS] Using {len(transcript)} transcript messages")
        else:
            logger.info(f"💬 [INSIGHTS] No transcript available")
        
        # Create prompt for Claude
        prompt = f"""You are analyzing an escalation decision that requires human judgment. Provide concise, actionable insights about the implications of this decision.

ESCALATION DETAILS:
- Type: {decision_type}
- Urgency: {urgency}
- Reason: {reason}
{f"- Additional Context: {context_details}" if context_details else ""}

RECENT CONVERSATION:
{conversation_context if conversation_context else "No recent conversation available"}

Provide 2-4 bullet points analyzing:
1. Strategic implications (e.g., "If approved, consider impact on other clients")
2. Risks or concerns to be aware of
3. Factors that support or oppose the decision
4. Any precedent or pattern considerations

Keep insights concise (1-2 sentences each). Focus on actionable intelligence that helps the operator make an informed decision."""

        logger.info(f"🚀 [INSIGHTS] Calling Claude API for escalation {escalation_id}...")
        logger.debug(f"📝 [INSIGHTS] Prompt length: {len(prompt)} chars")
        
        # Call Claude API with fast model (haiku - fastest Claude model)
        # Run in thread pool to avoid blocking the event loop
        def call_claude():
            return claude_client.messages.create(
                model="claude-3-haiku-20240307",  # Fast model for quick insights
                max_tokens=500,
                temperature=0.7,  # Slight creativity for better insights
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
        
        import concurrent.futures
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            response = await loop.run_in_executor(executor, call_claude)
        
        logger.info(f"✅ [INSIGHTS] Claude API response received for {escalation_id}")
        logger.debug(f"📦 [INSIGHTS] Response content type: {type(response.content)}")
        logger.debug(f"📦 [INSIGHTS] Response content length: {len(response.content) if response.content else 0}")
        
        insights = response.content[0].text if response.content else None
        
        if insights:
            logger.info(f"💡 [INSIGHTS] Successfully generated insights for {escalation_id} ({len(insights)} chars)")
            logger.debug(f"📄 [INSIGHTS] Insights preview: {insights[:100]}...")
        else:
            logger.warning(f"⚠️ [INSIGHTS] No insights text in response for {escalation_id}")
        
        return insights
        
    except Exception as e:
        logger.error(f"❌ [INSIGHTS] Failed to generate insights for {escalation_id}: {e}", exc_info=True)
        import traceback
        logger.error(f"📚 [INSIGHTS] Traceback: {traceback.format_exc()}")
        return None

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "LiveKit Token API is running"}

# ==================== ESCALATION ENDPOINTS ====================

@app.post("/api/escalations", response_model=EscalationResponse)
async def create_escalation(request: EscalationRequest):
    """Create a new escalation. Called by the agent."""
    escalation_id = f"esc_{uuid.uuid4().hex[:12]}"
    
    escalation = {
        "escalation_id": escalation_id,
        "room_name": request.room_name,
        "user_id": request.user_id,
        "reason": request.reason,
        "urgency": request.urgency,
        "decision_type": request.decision_type,
        "context_details": request.context_details,
        "recent_transcript": request.recent_transcript,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "human_response": None,
        "responded_at": None,
        "ai_insights": None,  # Will be populated asynchronously
        "insights_generated_at": None,
    }
    
    escalations[escalation_id] = escalation
    
    logger.info(f"🚨 New escalation created: {escalation_id} (urgency: {request.urgency})")
    
    # Notify all connected frontend clients immediately (without insights)
    await broadcast_to_frontend({
        "type": "new_escalation",
        "escalation": escalation
    })
    
    # Generate insights asynchronously (non-blocking)
    logger.info(f"🚀 [ESCALATION] Starting async insight generation task for {escalation_id}")
    task = asyncio.create_task(generate_and_update_insights(escalation_id, escalation))
    logger.info(f"✅ [ESCALATION] Insight generation task created for {escalation_id} (task: {task})")
    
    return EscalationResponse(escalation_id=escalation_id, status="pending")

async def generate_and_update_insights(escalation_id: str, escalation: dict):
    """Generate insights and update escalation record, then notify frontend."""
    logger.info(f"🎯 [INSIGHTS] Task started for escalation {escalation_id}")
    
    try:
        insights = await generate_decision_insights(escalation)
        
        logger.info(f"🔄 [INSIGHTS] Checking if escalation {escalation_id} still exists...")
        if escalation_id not in escalations:
            logger.warning(f"⚠️ [INSIGHTS] Escalation {escalation_id} no longer exists - skipping update")
            return
        
        if insights:
            escalations[escalation_id]["ai_insights"] = insights
            escalations[escalation_id]["insights_generated_at"] = datetime.now().isoformat()
            
            logger.info(f"💡 [INSIGHTS] Updated escalation {escalation_id} with insights")
            logger.info(f"📊 [INSIGHTS] Frontend WebSocket connections: {len(frontend_websockets)}")
            
            # Notify frontend that insights are available
            message = {
                "type": "insights_updated",
                "escalation_id": escalation_id,
                "escalation": escalations[escalation_id]
            }
            logger.info(f"📤 [INSIGHTS] Broadcasting insights update for {escalation_id} to {len(frontend_websockets)} frontend clients")
            await broadcast_to_frontend(message)
            logger.info(f"✅ [INSIGHTS] Successfully broadcasted insights for {escalation_id}")
        else:
            logger.warning(f"⚠️ [INSIGHTS] No insights generated for {escalation_id} - not updating")
            
    except Exception as e:
        logger.error(f"❌ [INSIGHTS] Error in generate_and_update_insights for {escalation_id}: {e}", exc_info=True)
        import traceback
        logger.error(f"📚 [INSIGHTS] Traceback: {traceback.format_exc()}")

@app.get("/api/escalations/pending")
async def get_pending_escalations():
    """Get all pending escalations. Called by frontend."""
    pending = [
        esc for esc in escalations.values()
        if esc["status"] == "pending"
    ]
    # Sort by urgency and creation time
    urgency_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    pending.sort(key=lambda x: (urgency_order.get(x["urgency"], 99), x["created_at"]))
    return {"escalations": pending}

@app.get("/api/escalations/{escalation_id}")
async def get_escalation(escalation_id: str):
    """Get a specific escalation by ID."""
    if escalation_id not in escalations:
        raise HTTPException(status_code=404, detail="Escalation not found")
    return escalations[escalation_id]

@app.post("/api/escalations/{escalation_id}/respond")
async def respond_to_escalation(escalation_id: str, request: HumanResponseRequest):
    """Submit a human response to an escalation. Called by frontend."""
    if escalation_id not in escalations:
        raise HTTPException(status_code=404, detail="Escalation not found")
    
    escalation = escalations[escalation_id]
    
    if escalation["status"] != "pending":
        raise HTTPException(status_code=400, detail="Escalation already resolved")
    
    escalation["human_response"] = request.response_text
    escalation["status"] = "resolved"
    escalation["responded_at"] = datetime.now().isoformat()
    
    logger.info(f"✅ Escalation {escalation_id} resolved with response")
    logger.info(f"📤 Response text: {request.response_text}")
    
    # Notify the agent via WebSocket if connected
    if escalation_id in agent_websockets:
        try:
            logger.info(f"🔌 Sending response via WebSocket for {escalation_id}")
            await agent_websockets[escalation_id].send_json({
                "type": "response_received",
                "escalation_id": escalation_id,
                "response": request.response_text
            })
        except Exception as e:
            logger.error(f"Failed to send response to agent: {e}")
    
    # Notify all frontend clients
    await broadcast_to_frontend({
        "type": "escalation_resolved",
        "escalation_id": escalation_id,
        "escalation": escalation
    })
    
    return {"status": "success", "message": "Response submitted"}

@app.delete("/api/escalations/{escalation_id}")
async def delete_escalation(escalation_id: str):
    """Delete an escalation. Called by frontend."""
    if escalation_id not in escalations:
        raise HTTPException(status_code=404, detail="Escalation not found")
    
    escalation = escalations[escalation_id]
    
    # Only allow deletion of pending escalations
    if escalation["status"] != "pending":
        raise HTTPException(status_code=400, detail="Can only delete pending escalations")
    
    # Remove from storage
    del escalations[escalation_id]
    
    logger.info(f"🗑️ Escalation {escalation_id} deleted")
    
    # Close agent WebSocket if connected
    if escalation_id in agent_websockets:
        try:
            await agent_websockets[escalation_id].close()
        except Exception as e:
            logger.error(f"Failed to close agent WebSocket: {e}")
        finally:
            agent_websockets.pop(escalation_id, None)
    
    # Notify all frontend clients
    await broadcast_to_frontend({
        "type": "escalation_deleted",
        "escalation_id": escalation_id
    })
    
    return {"status": "success", "message": "Escalation deleted"}

# ==================== WEBSOCKET ENDPOINTS ====================

async def broadcast_to_frontend(message: dict):
    """Broadcast a message to all connected frontend clients."""
    if not frontend_websockets:
        logger.warning(f"⚠️ [BROADCAST] No frontend WebSocket connections available")
        return
    
    message_type = message.get("type", "unknown")
    logger.info(f"📡 [BROADCAST] Broadcasting {message_type} to {len(frontend_websockets)} frontend clients")
    
    disconnected = set()
    success_count = 0
    for ws in frontend_websockets:
        try:
            await ws.send_json(message)
            success_count += 1
            logger.debug(f"✅ [BROADCAST] Sent {message_type} to frontend client")
        except Exception as e:
            logger.warning(f"❌ [BROADCAST] Failed to send {message_type} to frontend client: {e}")
            disconnected.add(ws)
    
    # Remove disconnected clients
    if disconnected:
        frontend_websockets.difference_update(disconnected)
        logger.info(f"🧹 [BROADCAST] Removed {len(disconnected)} disconnected clients")
    
    logger.info(f"📊 [BROADCAST] Successfully sent {message_type} to {success_count}/{len(frontend_websockets) + len(disconnected)} clients")

@app.websocket("/ws/agent/{escalation_id}")
async def agent_websocket_endpoint(websocket: WebSocket, escalation_id: str):
    """WebSocket endpoint for agents to receive responses in real-time."""
    await websocket.accept()
    agent_websockets[escalation_id] = websocket
    logger.info(f"🤖 Agent connected for escalation {escalation_id}")
    
    try:
        # Send current status if escalation exists and is resolved
        if escalation_id in escalations:
            escalation = escalations[escalation_id]
            if escalation["status"] == "resolved" and escalation["human_response"]:
                await websocket.send_json({
                    "type": "response_received",
                    "escalation_id": escalation_id,
                    "response": escalation["human_response"]
                })
        
        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            # Agent can send ping/pong or status updates
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        logger.info(f"🤖 Agent disconnected for escalation {escalation_id}")
    except Exception as e:
        logger.error(f"Error in agent WebSocket: {e}")
    finally:
        agent_websockets.pop(escalation_id, None)

@app.websocket("/ws/frontend")
async def frontend_websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for frontend to receive real-time escalation updates."""
    await websocket.accept()
    frontend_websockets.add(websocket)
    logger.info(f"🖥️ Frontend client connected (total: {len(frontend_websockets)})")
    
    try:
        # Send all pending escalations on connect
        pending = [
            esc for esc in escalations.values()
            if esc["status"] == "pending"
        ]
        await websocket.send_json({
            "type": "initial_state",
            "escalations": pending
        })
        
        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Frontend can send ping/pong
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        logger.info("🖥️ Frontend client disconnected")
    except Exception as e:
        logger.error(f"Error in frontend WebSocket: {e}")
    finally:
        frontend_websockets.discard(websocket)

@app.post("/api/livekit-token", response_model=TokenResponse)
async def create_token(request: TokenRequest):
    """
    Generate a LiveKit access token for a user to join a room.
    """
    try:
        # Get LiveKit credentials from environment
        livekit_api_key = os.getenv("LIVEKIT_API_KEY")
        livekit_api_secret = os.getenv("LIVEKIT_API_SECRET")
        livekit_url = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
        
        if not livekit_api_key or not livekit_api_secret:
            logger.error("LIVEKIT_API_KEY or LIVEKIT_API_SECRET not set in environment")
            raise HTTPException(
                status_code=500,
                detail="LiveKit credentials not configured on server"
            )
        
        # Create access token with room permissions
        token = (
            api.AccessToken(livekit_api_key, livekit_api_secret)
            .with_identity(request.participant_name)
            .with_name(request.participant_name)
            .with_grants(
                api.VideoGrants(
                    room_join=True,
                    room=request.room_name,
                    can_publish=True,
                    can_subscribe=True,
                    can_publish_data=True,
                )
            )
            .with_ttl(timedelta(hours=2))
        )
        
        # Add metadata if user_id provided
        if request.user_id:
            token.with_metadata(request.user_id)
        
        jwt_token = token.to_jwt()
        
        logger.info(f"✅ Generated token for {request.participant_name} in room {request.room_name}")
        
        return TokenResponse(
            token=jwt_token,
            url=livekit_url
        )
        
    except Exception as e:
        logger.error(f"❌ Error generating token: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    
    logger.info("=== STARTING API SERVER ===")
    logger.info(f"LIVEKIT_URL: {os.getenv('LIVEKIT_URL', 'ws://localhost:7880')}")
    logger.info(f"LIVEKIT_API_KEY: {'✅ SET' if os.getenv('LIVEKIT_API_KEY') else '❌ NOT SET'}")
    logger.info(f"LIVEKIT_API_SECRET: {'✅ SET' if os.getenv('LIVEKIT_API_SECRET') else '❌ NOT SET'}")
    logger.info(f"ANTHROPIC_API_KEY: {'✅ SET' if os.getenv('ANTHROPIC_API_KEY') else '❌ NOT SET'}")
    logger.info(f"CLAUDE_API_KEY: {'✅ SET' if os.getenv('CLAUDE_API_KEY') else '❌ NOT SET'}")
    logger.info(f"Claude Client Status: {'✅ INITIALIZED' if claude_client else '❌ NOT INITIALIZED'}")
    logger.info("===========================")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )


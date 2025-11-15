#!/usr/bin/env python3

import os
import logging
from datetime import timedelta
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from livekit import api

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

# Request/Response models
class TokenRequest(BaseModel):
    room_name: str
    participant_name: str
    user_id: str | None = None

class TokenResponse(BaseModel):
    token: str
    url: str

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "LiveKit Token API is running"}

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
    logger.info("===========================")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )


#!/usr/bin/env python3

import logging
import os
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
from pathlib import Path

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RoomInputOptions,
    WorkerOptions,
    cli,
)
from livekit.plugins import google
import google.generativeai as genai

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("simple-agent")

# Reduce noise from verbose libraries
logging.getLogger("hpack").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

logger.info("=== ENVIRONMENT VARIABLES CHECK ===")
logger.info(f"GOOGLE_API_KEY: {'✅ SET' if os.getenv('GOOGLE_API_KEY') else '❌ NOT SET'}")
logger.info(f"LIVEKIT_URL: {os.getenv('LIVEKIT_URL', '❌ NOT SET')}")
logger.info(f"LIVEKIT_API_KEY: {'✅ SET' if os.getenv('LIVEKIT_API_KEY') else '❌ NOT SET'}")
logger.info(f"LIVEKIT_API_SECRET: {'✅ SET' if os.getenv('LIVEKIT_API_SECRET') else '❌ NOT SET'}")
logger.info("=====================================")

# Configure Gemini API
google_api_key = os.getenv('GOOGLE_API_KEY')
if google_api_key:
    genai.configure(api_key=google_api_key)
    logger.info("✅ Gemini API configured")
else:
    logger.warning("❌ GOOGLE_API_KEY not found")


class SimpleAgent(Agent):
    """A minimal agent for transcription-based conversations."""
    
    def __init__(self, user_id: str = "default_user") -> None:
        self.user_id = user_id
        
        # Initialize basic instructions
        instructions = self._get_instructions()
        
        super().__init__(
            instructions=instructions,
            llm=google.beta.realtime.RealtimeModel(
                model="gemini-2.5-flash-native-audio-preview-09-2025",
                voice="Zephyr",
                temperature=0.9,
                instructions=instructions,
            ),
        )
        
        # Transcript storage
        self.transcript: List[Dict[str, Any]] = []
        self.session_start_time = datetime.now()
        self.room_name = ""
    
    def _get_instructions(self) -> str:
        """Return basic conversation instructions."""
        return """You are a warm and helpful conversation partner. 
Engage naturally with the user, listen actively, and respond thoughtfully to what they share.
Be supportive and genuine in your interactions."""
    
    async def on_enter(self):
        """Called when the agent enters the room."""
        logger.info("🚀 Agent entered the room")
        
        # Set up conversation listener for transcriptions
        @self.session.on("conversation_item_added")
        def on_conversation_item_added(event):
            self._on_conversation_item_added(event)
        
        # Set up session close handler
        @self.session.on("close")
        def on_session_close(event):
            logger.info("Session closed")
            self._print_transcript()
        
        # Send greeting
        logger.info("👋 Sending greeting...")
        self.session.generate_reply(instructions="Greet the user warmly and naturally. Ask how they're doing.")
        logger.info("✅ Agent initialized")
    
    def _on_conversation_item_added(self, event):
        """Handle new conversation items (transcriptions)."""
        try:
            item = event.item
            timestamp = datetime.now()
            
            # Extract text content from the item
            content_text = ""
            if hasattr(item, 'text_content') and item.text_content:
                content_text = item.text_content
            elif hasattr(item, 'content'):
                if isinstance(item.content, str):
                    content_text = item.content
                elif isinstance(item.content, list):
                    for content in item.content:
                        if hasattr(content, 'text') and content.text:
                            content_text += content.text
            
            # Skip empty content
            if not content_text.strip():
                return
            
            # Store transcript entry
            transcript_entry = {
                "timestamp": timestamp.isoformat(),
                "role": item.role,  # "user" or "assistant"
                "content": content_text.strip(),
            }
            
            self.transcript.append(transcript_entry)
            logger.info(f"[{item.role.upper()}] {content_text[:50]}...")
            
        except Exception as e:
            logger.error(f"Error processing conversation item: {e}")
    
    def _print_transcript(self):
        """Print the full transcript."""
        logger.info("\n" + "="*60)
        logger.info("📝 CONVERSATION TRANSCRIPT")
        logger.info("="*60)
        
        for msg in self.transcript:
            role = "USER" if msg["role"] == "user" else "AGENT"
            timestamp = msg["timestamp"]
            content = msg["content"]
            logger.info(f"[{timestamp}] {role}: {content}")
        
        logger.info("="*60)
        logger.info(f"Total messages: {len(self.transcript)}")
        duration = (datetime.now() - self.session_start_time).total_seconds() / 60
        logger.info(f"Session duration: {duration:.2f} minutes")
        logger.info("="*60 + "\n")
    
    async def on_session_end(self):
        """Called when the session ends."""
        logger.info("Session ending")
        self._print_transcript()


def get_or_create_test_user_id():
    """Get or create a persistent test user ID for development."""
    user_id_file = Path(__file__).parent / "test_user_id.txt"
    
    if user_id_file.exists():
        try:
            with open(user_id_file, 'r') as f:
                user_id = f.read().strip()
                if user_id:
                    logger.info(f"🔄 Using existing test user: {user_id}")
                    return user_id
        except Exception as e:
            logger.warning(f"⚠️ Could not read test user ID: {e}")
    
    import uuid
    user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    
    try:
        with open(user_id_file, 'w') as f:
            f.write(user_id)
        logger.info(f"✨ Created new test user: {user_id}")
    except Exception as e:
        logger.error(f"❌ Could not save test user ID: {e}")
    
    return user_id


async def entrypoint(ctx: JobContext):
    """Main entry point for the agent."""
    logger.info("Starting Simple Agent")
    
    # Connect to the room
    await ctx.connect()
    
    # Get user ID
    user_id = get_or_create_test_user_id()
    logger.info(f"🆔 User ID: {user_id}")
    
    # Create and start the agent
    agent = SimpleAgent(user_id=user_id)
    agent.ctx = ctx
    session = AgentSession()
    
    try:
        await session.start(
            agent=agent,
            room=ctx.room,
            room_input_options=RoomInputOptions(
                video_enabled=True,
            ),
        )
    except Exception as e:
        logger.error(f"Session error: {e}")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))


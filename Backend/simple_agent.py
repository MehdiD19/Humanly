#!/usr/bin/env python3

import logging
import os
import json
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
from pathlib import Path

from livekit import agents
from livekit.agents import AgentSession, Agent, WorkerOptions, RoomInputOptions, function_tool, RunContext
from livekit.plugins import noise_cancellation, silero

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
logger.info(f"DEEPGRAM_API_KEY: {'✅ SET' if os.getenv('DEEPGRAM_API_KEY') else '❌ NOT SET'}")
logger.info(f"ELEVENLABS_API_KEY: {'✅ SET' if os.getenv('ELEVENLABS_API_KEY') else '❌ NOT SET'}")
logger.info(f"LIVEKIT_URL: {os.getenv('LIVEKIT_URL', '❌ NOT SET')}")
logger.info(f"LIVEKIT_API_KEY: {'✅ SET' if os.getenv('LIVEKIT_API_KEY') else '❌ NOT SET'}")
logger.info(f"LIVEKIT_API_SECRET: {'✅ SET' if os.getenv('LIVEKIT_API_SECRET') else '❌ NOT SET'}")
logger.info("=====================================")


class Assistant(Agent):
    """A voice AI assistant using STT-LLM-TTS pipeline with human escalation detection."""
    
    def __init__(self, user_id: str = "default_user") -> None:
        self.user_id = user_id
        
        super().__init__(
            instructions="""You are a warm and helpful conversation partner. 
Engage naturally with the user, listen actively, and respond thoughtfully to what they share.
Be supportive and genuine in your interactions.
Your responses are concise, to the point, and conversational.
Avoid complex formatting, punctuation, emojis, asterisks, or other symbols.

IMPORTANT: When you encounter situations that require human decision-making, authorization, 
or when you lack critical information to properly assist the user, you MUST use the 
escalate_to_human function. This includes:
- Financial decisions or offers (e.g., "Do you accept the 10,000 euro offer?")
- Authorization requests (payments, contracts, sensitive actions)
- Questions you cannot confidently answer
- Sensitive personal, medical, or legal matters
- High-stakes decisions that could have significant consequences""",
        )
        
        # Transcript storage
        self.transcript: List[Dict[str, Any]] = []
        self.session_start_time = datetime.now()
        
        # Escalation tracking
        self.escalations: List[Dict[str, Any]] = []
    
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
    
    @function_tool()
    async def escalate_to_human(
        self,
        context: RunContext,
        reason: str,
        urgency: str,
        decision_type: str,
        context_details: str = ""
    ):
        """Flag a moment in the conversation that requires human intervention or decision-making.
        
        Use this function when you encounter:
        - Financial decisions (accepting offers, authorizing payments, budget approvals)
        - Authorization requests (signing contracts, approving transactions)
        - Information gaps where you lack critical knowledge to help the user
        - Sensitive topics (medical, legal, personal matters requiring professional judgment)
        - High-stakes decisions with significant consequences
        - User explicitly requesting to speak with a human
        
        Args:
            reason: Clear explanation of why human intervention is needed (2-3 sentences)
            urgency: How urgent this escalation is - must be one of: "low", "medium", "high", "critical"
            decision_type: Category of the escalation - must be one of: 
                          "financial", "authorization", "information_gap", "sensitive_topic", "user_request"
            context_details: Additional relevant details or information (optional)
        
        Returns:
            Confirmation that the escalation has been logged
        """
        
        # Validate urgency
        valid_urgency = ["low", "medium", "high", "critical"]
        if urgency.lower() not in valid_urgency:
            urgency = "medium"  # Default fallback
        
        # Validate decision type
        valid_types = ["financial", "authorization", "information_gap", "sensitive_topic", "user_request"]
        if decision_type.lower() not in valid_types:
            decision_type = "information_gap"  # Default fallback
        
        # Create escalation record
        escalation = {
            "timestamp": datetime.now().isoformat(),
            "user_id": self.user_id,
            "reason": reason,
            "urgency": urgency.lower(),
            "decision_type": decision_type.lower(),
            "context_details": context_details,
            "recent_transcript": self.transcript[-5:] if len(self.transcript) >= 5 else self.transcript,
        }
        
        # Store escalation
        self.escalations.append(escalation)
        
        # Log the escalation prominently
        logger.warning("\n" + "="*80)
        logger.warning("🚨 HUMAN ESCALATION DETECTED 🚨")
        logger.warning("="*80)
        logger.warning(f"User ID: {self.user_id}")
        logger.warning(f"Urgency: {urgency.upper()}")
        logger.warning(f"Type: {decision_type}")
        logger.warning(f"Reason: {reason}")
        if context_details:
            logger.warning(f"Details: {context_details}")
        logger.warning("-" * 80)
        logger.warning("Recent conversation context:")
        for msg in escalation["recent_transcript"]:
            logger.warning(f"  [{msg['role'].upper()}] {msg['content'][:100]}")
        logger.warning("="*80 + "\n")
        
        # Save to file for persistence
        self._save_escalation_to_file(escalation)
        
        # TODO: In production, you would:
        # - Send webhook notification
        # - Store in database
        # - Trigger alert to human operator
        # - Update dashboard
        # - Send to message queue (e.g., RabbitMQ, Redis)
        
        return f"I've flagged this for human assistance. This has been recorded as a {urgency} priority {decision_type} escalation."
    
    def _save_escalation_to_file(self, escalation: Dict[str, Any]):
        """Save escalation to a JSON file for review."""
        try:
            escalations_file = Path(__file__).parent / "escalations.json"
            
            # Load existing escalations
            existing_escalations = []
            if escalations_file.exists():
                try:
                    with open(escalations_file, 'r') as f:
                        existing_escalations = json.load(f)
                except json.JSONDecodeError:
                    existing_escalations = []
            
            # Append new escalation
            existing_escalations.append(escalation)
            
            # Save back to file
            with open(escalations_file, 'w') as f:
                json.dump(existing_escalations, f, indent=2)
            
            logger.info(f"✅ Escalation saved to {escalations_file}")
        except Exception as e:
            logger.error(f"❌ Failed to save escalation to file: {e}")
    
    async def on_session_end(self):
        """Called when the session ends."""
        logger.info("Session ending")
        self._print_transcript()
        self._print_escalations_summary()
    
    def _print_escalations_summary(self):
        """Print summary of all escalations during the session."""
        if not self.escalations:
            return
        
        logger.info("\n" + "="*40)
        logger.info("🚨 ESCALATIONS SUMMARY")
        logger.info("="*40)
        logger.info(f"Total escalations: {len(self.escalations)}")
        
        for idx, escalation in enumerate(self.escalations, 1):
            logger.info(f"\n--- Escalation #{idx} ---")
            logger.info(f"Time: {escalation['timestamp']}")
            logger.info(f"Urgency: {escalation['urgency'].upper()}")
            logger.info(f"Type: {escalation['decision_type']}")
            logger.info(f"Reason: {escalation['reason']}")
            if escalation['context_details']:
                logger.info(f"Details: {escalation['context_details']}")
        
        logger.info("="*60 + "\n")


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


async def entrypoint(ctx: agents.JobContext):
    """Main entry point for the agent."""
    logger.info("Starting STT-LLM-TTS Pipeline Agent")
    logger.info("🎤 STT: Deepgram")
    logger.info("🧠 LLM: Google Gemini")
    logger.info("🔊 TTS: Eleven Labs")
    
    # Get user ID
    user_id = get_or_create_test_user_id()
    logger.info(f"🆔 User ID: {user_id}")
    
    # Create agent session with pipeline configuration
    session = AgentSession(
        stt="deepgram/nova-3:en",
        llm="google/gemini-2.5-flash",
        tts="elevenlabs/eleven_turbo_v2_5:Xb7hH8MSUJpSbSDYk0k2",  # Default voice
        vad=silero.VAD.load(),
    )
    
    # Create the assistant
    assistant = Assistant(user_id=user_id)
    
    # Start the session
    await session.start(
        room=ctx.room,
        agent=assistant,
        room_input_options=RoomInputOptions(
            video_enabled=True,
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )
    
    # Send initial greeting
    logger.info("👋 Sending greeting...")
    await session.generate_reply(
        instructions="Greet the user warmly and naturally. Ask how they're doing."
    )


if __name__ == "__main__":
    agents.cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))

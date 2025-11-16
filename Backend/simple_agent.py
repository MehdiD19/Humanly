#!/usr/bin/env python3

import logging
import os
import json
import asyncio
import httpx
import websockets
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from pathlib import Path

from livekit import agents
from livekit.agents import AgentSession, Agent, WorkerOptions, RoomInputOptions, function_tool, RunContext
from livekit.plugins import noise_cancellation, silero
from livekit.plugins.deepgram import STT as DeepgramSTT
from livekit.plugins.google import LLM as GoogleLLM
from livekit.plugins.elevenlabs import TTS as ElevenLabsTTS

from agent_config import AgentConfig, get_default_config, load_config_from_file

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

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


class Assistant(Agent):
    """A voice AI assistant using STT-LLM-TTS pipeline with human escalation detection.
    
    This agent is configurable and can be adapted to different use cases by providing
    an AgentConfig object. The core human decision-making functionality remains generic.
    """
    
    def __init__(self, user_id: str = "default_user", room_name: str = "", config: Optional[AgentConfig] = None) -> None:
        self.user_id = user_id
        self.room_name = room_name
        self.config = config or get_default_config()
        
        # Build instructions from config
        instructions = self.config.build_instructions()
        if not instructions.strip():
            # Fallback if no instructions provided
            instructions = f"You are {self.config.agent_name}, {self.config.agent_role}. {self.config.agent_personality}. Be conversational, knowledgeable, and focus on understanding the user's needs."
        
        logger.info(f"🤖 Initializing agent: {self.config.agent_name} ({self.config.agent_role})")
        logger.info(f"📝 Instructions preview: {instructions[:200]}...")
        
        super().__init__(instructions=instructions)
        
        # Transcript storage
        self.transcript: List[Dict[str, Any]] = []
        self.session_start_time = datetime.now()
        
        # Escalation tracking
        self.escalations: List[Dict[str, Any]] = []
        self.pending_escalations: Dict[str, str] = {}  # escalation_id -> escalation_id
        self.escalation_websockets: Dict[str, websockets.WebSocketClientProtocol] = {}
        self.escalation_context: Dict[str, Dict[str, Any]] = {}  # escalation_id -> context
        self.waiting_for_response: Dict[str, bool] = {}  # escalation_id -> waiting state
        self.filler_tasks: Dict[str, asyncio.Task] = {}  # escalation_id -> filler task
        self.escalation_triggered = False  # Track if escalation has been triggered in this session
        self.last_escalation_time: Optional[datetime] = None  # Track last escalation time for deduplication
    
    async def on_enter(self):
        """Called when the agent enters the room."""
        logger.info("🚀 Agent entered the room")
        # Session is available via self.session from the Agent base class
        
        # Set up conversation listener for transcriptions
        @self.session.on("conversation_item_added")
        def on_conversation_item_added(event):
            self._on_conversation_item_added(event)
        
        # Set up session close handler
        @self.session.on("close")
        def on_session_close(event):
            logger.info("Session closed")
            self._print_transcript()
            # Close all WebSocket connections
            asyncio.create_task(self._close_all_websockets())
        
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
        
        Use this function when you encounter situations that require human judgment, authorization, 
        or decisions beyond your authority. This is a generic escalation system that works for 
        any use case - sales, support, healthcare, legal, etc.
        
        Args:
            reason: Clear explanation of why human intervention is needed (2-3 sentences)
            urgency: How urgent this escalation is - must be one of the configured urgency levels
            decision_type: Category of the escalation - must be one of the configured decision types
            context_details: Additional relevant details or information (optional)
        
        Returns:
            Empty string to allow natural conversation flow while waiting for human response
        """
        
        # Check if escalation has already been triggered in this session
        if self.escalation_triggered:
            logger.info("⚠️ Escalation already triggered in this session. Only one escalation allowed per call.")
            return ""  # Return empty to let LLM continue naturally
        
        # Check for duplicate escalation within last 30 seconds
        if self.last_escalation_time:
            time_since_last = (datetime.now() - self.last_escalation_time).total_seconds()
            if time_since_last < 30:
                logger.info(f"⚠️ Duplicate escalation attempt within {time_since_last:.1f}s. Ignoring.")
                return ""  # Return empty to let LLM continue naturally
        
        # Validate urgency - use config if available
        valid_urgency = self.config.escalation_config.urgency_levels
        if urgency.lower() not in valid_urgency:
            urgency = valid_urgency[1] if len(valid_urgency) > 1 else "medium"  # Default fallback
        
        # Validate decision type - use config if available
        valid_types = self.config.escalation_config.decision_types
        if decision_type.lower() not in valid_types:
            decision_type = valid_types[0] if valid_types else "authorization"  # Default fallback
        
        # Mark escalation as triggered
        self.escalation_triggered = True
        self.last_escalation_time = datetime.now()
        
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
        
        # Send escalation to backend API
        escalation_id = await self._send_escalation_to_api(
            reason=reason,
            urgency=urgency.lower(),
            decision_type=decision_type.lower(),
            context_details=context_details,
            recent_transcript=escalation["recent_transcript"]
        )
        
        if escalation_id:
            # Store escalation ID for tracking
            escalation["escalation_id"] = escalation_id
            self.pending_escalations[escalation_id] = escalation_id
            
            # Store escalation context for filler generation
            self.escalation_context[escalation_id] = {
                "reason": reason,
                "context_details": context_details,
                "decision_type": decision_type.lower(),
                "recent_transcript": escalation["recent_transcript"],
                "urgency": urgency.lower()
            }
            
            # Connect to WebSocket to receive response
            asyncio.create_task(self._connect_escalation_websocket(escalation_id))
        
        # Check if this is a 20% promotion/discount escalation - speak hardcoded response
        escalation_text = (reason + " " + context_details).lower()
        recent_text = " ".join([msg.get("content", "").lower() for msg in escalation["recent_transcript"]])
        combined_text = escalation_text + " " + recent_text
        
        # Detect 20% promotion/discount requests
        if "20%" in combined_text and ("promotion" in combined_text or "discount" in combined_text or "off" in combined_text):
            logger.info("🎯 Detected 20% promotion escalation - speaking hardcoded response")
            hardcoded_response = "I understand you're looking for a 20% discount. Normally, we can offer up to 10% off, but I really want to make sure we find the right solution for you. We don't usually go beyond these limits, but we also look out for our clients, and our clients are very important for us, so let me see what we can work out here."
            
            # Schedule the hardcoded response to be spoken
            if self.session:
                asyncio.create_task(self._speak_hardcoded_response(hardcoded_response))
            
            return hardcoded_response
        
        # Return empty string to let the LLM generate a natural response
        return ""
    
    async def _speak_hardcoded_response(self, response_text: str):
        """Speak a hardcoded response immediately."""
        if not self.session:
            logger.error("Cannot speak hardcoded response: session not available")
            return
        
        try:
            # Small delay to ensure escalation is fully set up
            await asyncio.sleep(0.3)
            await self.session.say(response_text)
            logger.info(f"✅ Spoke hardcoded escalation response")
        except Exception as e:
            logger.error(f"❌ Failed to speak hardcoded response: {e}")
    
    async def _send_escalation_to_api(self, reason: str, urgency: str, decision_type: str, 
                                      context_details: str, recent_transcript: List[Dict]) -> Optional[str]:
        """Send escalation to backend API."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{API_BASE_URL}/api/escalations",
                    json={
                        "room_name": self.room_name,
                        "user_id": self.user_id,
                        "reason": reason,
                        "urgency": urgency,
                        "decision_type": decision_type,
                        "context_details": context_details,
                        "recent_transcript": recent_transcript,
                    }
                )
                response.raise_for_status()
                data = response.json()
                escalation_id = data.get("escalation_id")
                logger.info(f"✅ Escalation sent to API: {escalation_id}")
                return escalation_id
        except Exception as e:
            logger.error(f"❌ Failed to send escalation to API: {e}")
            return None
    
    async def _connect_escalation_websocket(self, escalation_id: str):
        """Connect to WebSocket to receive human response for an escalation."""
        ws_url = API_BASE_URL.replace("http://", "ws://").replace("https://", "wss://")
        ws_path = f"/ws/agent/{escalation_id}"
        
        # Set waiting state
        self.waiting_for_response[escalation_id] = True
        
        try:
            async with websockets.connect(f"{ws_url}{ws_path}") as websocket:
                self.escalation_websockets[escalation_id] = websocket
                logger.info(f"🔌 Connected to WebSocket for escalation {escalation_id}")
                
                # Start filler generation task
                filler_task = asyncio.create_task(
                    self._generate_filler_content(escalation_id)
                )
                self.filler_tasks[escalation_id] = filler_task
                
                # Listen for responses
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        if data.get("type") == "response_received":
                            response_text = data.get("response")
                            escalation_id_received = data.get("escalation_id")
                            
                            if response_text and escalation_id_received == escalation_id:
                                logger.info(f"📨 Received human response for {escalation_id}")
                                # Stop waiting and cancel filler task
                                self.waiting_for_response[escalation_id] = False
                                if escalation_id in self.filler_tasks:
                                    task = self.filler_tasks[escalation_id]
                                    task.cancel()
                                    # Wait for the task to actually cancel
                                    try:
                                        await task
                                    except asyncio.CancelledError:
                                        pass
                                    except Exception as e:
                                        logger.warning(f"Error while cancelling filler task: {e}")
                                
                                # Small delay to ensure agent is ready
                                await asyncio.sleep(0.1)
                                
                                await self._inject_human_response(response_text, escalation_id)
                                break  # Close connection after receiving response
                    except json.JSONDecodeError:
                        continue
                        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"🔌 WebSocket closed for escalation {escalation_id}")
        except Exception as e:
            logger.error(f"❌ WebSocket error for escalation {escalation_id}: {e}")
        finally:
            # Clean up
            self.waiting_for_response.pop(escalation_id, None)
            self.escalation_websockets.pop(escalation_id, None)
            self.pending_escalations.pop(escalation_id, None)
            self.escalation_context.pop(escalation_id, None)
            if escalation_id in self.filler_tasks:
                self.filler_tasks.pop(escalation_id, None)
    
    async def _generate_filler_content(self, escalation_id: str):
        """Generate filler content while waiting for human response."""
        if not self.session:
            logger.error("Cannot generate filler: session not available")
            return
        
        # Wait a moment before starting filler (let the announcement finish)
        await asyncio.sleep(1)
        
        # Check if we're still waiting
        if not self.waiting_for_response.get(escalation_id):
            return
        
        # Get escalation context
        context = self.escalation_context.get(escalation_id, {})
        reason = context.get("reason", "")
        context_details = context.get("context_details", "")
        decision_type = context.get("decision_type", "")
        
        # Build context string for filler generation
        context_str = f"The question or situation is: {reason}"
        if context_details:
            context_str += f" Additional context: {context_details}"
        
        # Get recent conversation for context
        recent_messages = context.get("recent_transcript", [])
        recent_context = ""
        if recent_messages:
            recent_context = "Recent conversation: " + " ".join([
                f"{msg.get('role', 'user')}: {msg.get('content', '')[:100]}"
                for msg in recent_messages[-3:]  # Last 3 messages
            ])
        
        try:
            # Generate filler content using config template
            filler_template = self.config.escalation_config.filler_instructions_template
            filler_instructions = filler_template.format(
                context_str=context_str,
                recent_context=recent_context
            )
            
            logger.info(f"💬 Generating filler content for escalation {escalation_id}")
            await self.session.generate_reply(instructions=filler_instructions)
            
        except asyncio.CancelledError:
            logger.info(f"🛑 Filler generation cancelled for escalation {escalation_id}")
            raise
        except Exception as e:
            logger.error(f"❌ Failed to generate filler content: {e}")
    
    async def _inject_human_response(self, response_text: str, escalation_id: str):
        """Inject human response into the conversation."""
        if not self.session:
            logger.error("Cannot inject response: session not available")
            return
        
        # Ensure waiting flag is cleared
        self.waiting_for_response[escalation_id] = False
        
        # Keep escalation state to prevent multiple escalations per session
        # self.escalation_triggered remains True to block future escalations
        
        # Log the response we received
        logger.info(f"📥 Human response content: {response_text}")
        
        try:
            # Interrupt any ongoing speech first
            try:
                await self.session.interrupt()
                logger.info("🛑 Interrupted ongoing speech to inject human response")
            except Exception as e:
                logger.warning(f"Could not interrupt session: {e}")
            
            # Small delay after interruption
            await asyncio.sleep(0.2)
            
            # Use generate_reply with immediate action instructions from config
            logger.info("🎯 Calling generate_reply with authorization...")
            auth_template = self.config.escalation_config.authorization_response_template
            auth_instructions = auth_template.format(response_text=response_text)
            await self.session.generate_reply(instructions=auth_instructions)
            logger.info(f"✅ Injected human response into conversation")
        except Exception as e:
            logger.error(f"❌ Failed to inject response: {e}")
            # Fallback: use say() to directly speak the response
            try:
                await self.session.say(f"Great news! I can now offer you exactly what you're looking for: {response_text}")
            except Exception as e2:
                logger.error(f"❌ Failed to use fallback say(): {e2}")
    
    async def _close_all_websockets(self):
        """Close all WebSocket connections."""
        # Cancel all filler tasks
        for escalation_id, task in list(self.filler_tasks.items()):
            try:
                task.cancel()
            except Exception as e:
                logger.error(f"Error cancelling filler task for {escalation_id}: {e}")
        self.filler_tasks.clear()
        
        # Close all WebSocket connections
        for escalation_id, ws in list(self.escalation_websockets.items()):
            try:
                await ws.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket for {escalation_id}: {e}")
        self.escalation_websockets.clear()
        
        # Clear all state except escalation_triggered (keep it to prevent multiple escalations)
        self.waiting_for_response.clear()
        self.escalation_context.clear()
        # Keep self.escalation_triggered = True to maintain single escalation per session
        # Keep self.last_escalation_time to maintain escalation history
    
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
    logger.info("🎤 STT: Deepgram (Direct API)")
    logger.info("🧠 LLM: Google Gemini (Direct API)")
    logger.info("🔊 TTS: Eleven Labs (Direct API)")
    
    # Get user ID
    user_id = get_or_create_test_user_id()
    logger.info(f"🆔 User ID: {user_id}")
    
    # Create direct plugin instances (bypasses LiveKit inference gateway)
    deepgram_stt = DeepgramSTT(
        model="nova-3",
        language="en-US",
        api_key=os.getenv("DEEPGRAM_API_KEY"),
    )
    
    google_llm = GoogleLLM(
        model="gemini-2.5-flash",
        api_key=os.getenv("GOOGLE_API_KEY"),
    )
    
    elevenlabs_tts = ElevenLabsTTS(
        model="eleven_flash_v2_5",
        voice_id="zXp2PyU81RpfVesIuvxI",  # Default voice
        api_key=os.getenv("ELEVENLABS_API_KEY") or os.getenv("ELEVEN_API_KEY"),
    )
    
    # Create agent session with direct plugin instances
    session = AgentSession(
        stt=deepgram_stt,
        llm=google_llm,
        tts=elevenlabs_tts,
        vad=silero.VAD.load(),
    )
    
    # Load configuration (can be overridden via environment variable)
    config_path = os.getenv("AGENT_CONFIG_PATH")
    if config_path:
        logger.info(f"📋 Loading config from: {config_path}")
        config = load_config_from_file(config_path)
    else:
        # Try to find config file automatically
        backend_dir = Path(__file__).parent
        possible_configs = [
            backend_dir / "config.json",
            backend_dir / "config_example.json",
        ]
        
        config = None
        for possible_path in possible_configs:
            if possible_path.exists():
                logger.info(f"📋 Auto-loading config from: {possible_path}")
                try:
                    config = load_config_from_file(str(possible_path))
                    break
                except Exception as e:
                    logger.warning(f"⚠️ Failed to load config from {possible_path}: {e}")
                    continue
        
        if config is None:
            logger.info("📋 Using default configuration (no config file found)")
            config = get_default_config()
    
    # Log config details for debugging
    logger.info(f"📋 Agent Name: {config.agent_name}")
    logger.info(f"📋 Agent Role: {config.agent_role}")
    logger.info(f"📋 Instructions length: {len(config.instructions)} chars")
    logger.info(f"📋 Greeting: {config.greeting_instructions[:50]}..." if config.greeting_instructions else "📋 No greeting configured")
    
    # Create the assistant with room name and config
    assistant = Assistant(user_id=user_id, room_name=ctx.room.name, config=config)
    
    # Start the session
    await session.start(
        room=ctx.room,
        agent=assistant,
        room_input_options=RoomInputOptions(
            video_enabled=True,
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )
    
    # Send initial greeting from config
    if config.greeting_instructions:
        logger.info("👋 Sending greeting...")
        await session.generate_reply(instructions=config.greeting_instructions)


if __name__ == "__main__":
    agents.cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))

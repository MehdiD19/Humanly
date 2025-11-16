"""
Agent Configuration Module

This module provides a generic configuration system for human decision-making agents.
The agent can be adapted to any use case by providing agent context and escalation rules.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
import json


@dataclass
class EscalationConfig:
    """Configuration for escalation behavior - defines when and how to escalate to humans."""
    
    # Decision types that require human intervention
    decision_types: List[str] = field(default_factory=lambda: [
        "authorization",
        "financial",
        "sensitive_topic",
        "user_request",
        "policy_exception",
        "custom_request"
    ])
    
    # Urgency levels for escalations
    urgency_levels: List[str] = field(default_factory=lambda: [
        "low",
        "medium",
        "high",
        "critical"
    ])
    
    # Instructions for what triggers escalation
    escalation_triggers: str = """Use escalate_to_human when:
- The request requires authorization beyond your normal authority
- Financial decisions need approval
- Sensitive topics require human judgment
- User explicitly requests to speak with a human
- Policy exceptions are needed
- Custom requests that fall outside standard procedures"""
    
    # Template for filler content while waiting for human response
    filler_instructions_template: str = """Continue the conversation naturally about the topic. {context_str}

{recent_context}

Acknowledge their request and explore the topic further. Be conversational and genuine. Never mention waiting, checking with teams, or needing approval - just continue the conversation naturally while the matter is being reviewed."""
    
    # Template for how to respond when human authorization is received
    authorization_response_template: str = """IMPORTANT: You have just received authorization: "{response_text}"

This authorization OVERRIDES your normal authority limits. Act on it IMMEDIATELY.

Respond right now with enthusiasm and confidence. Announce the approval or decision immediately. Be spontaneous and genuine. Act as if you just received this authorization and are excited to share it.

Respond RIGHT NOW with the authorized action or decision."""


@dataclass
class AgentConfig:
    """Generic configuration class for the agent.
    
    This configuration is domain-agnostic and focuses on:
    1. Agent context and personality
    2. When to escalate to humans
    3. How to handle escalations
    """
    
    # Agent identity and context
    agent_name: str = "Assistant"
    agent_role: str = "helpful assistant"
    agent_personality: str = "friendly, knowledgeable, and professional"
    
    # Main instructions - define the agent's purpose, knowledge, and behavior
    instructions: str = """You are a helpful assistant. Be conversational, knowledgeable, and focus on understanding the user's needs.

When you encounter situations that require human judgment, authorization, or decisions beyond your authority, use the escalate_to_human function."""
    
    # Authority limits - what the agent can and cannot do (generic)
    authority_limits: str = """You can:
- Answer questions based on your knowledge
- Provide information and guidance
- Help with standard procedures

You CANNOT:
- Make decisions requiring authorization
- Approve exceptions to policies
- Commit to actions beyond your authority
- Make financial decisions without approval"""
    
    # Escalation configuration
    escalation_config: EscalationConfig = field(default_factory=EscalationConfig)
    
    # Greeting instructions
    greeting_instructions: str = "Greet the user warmly and ask how you can help them today."
    
    def build_instructions(self) -> str:
        """Build the full instructions string from components."""
        parts = []
        
        # Add main instructions
        if self.instructions:
            parts.append(self.instructions)
        
        # Add authority limits
        if self.authority_limits:
            parts.append("\nYOUR AUTHORITY LIMITS:")
            parts.append(self.authority_limits)
        
        # Add escalation triggers
        if self.escalation_config.escalation_triggers:
            parts.append("\nESCALATION TRIGGERS:")
            parts.append(self.escalation_config.escalation_triggers)
        
        return "\n".join(parts)


def load_config_from_dict(config_dict: Dict[str, Any]) -> AgentConfig:
    """Load configuration from a dictionary."""
    
    # Parse escalation config
    esc_data = config_dict.get("escalation_config", {})
    escalation_config = EscalationConfig(
        decision_types=esc_data.get("decision_types", EscalationConfig().decision_types),
        urgency_levels=esc_data.get("urgency_levels", EscalationConfig().urgency_levels),
        escalation_triggers=esc_data.get("escalation_triggers", EscalationConfig().escalation_triggers),
        filler_instructions_template=esc_data.get("filler_instructions_template", EscalationConfig().filler_instructions_template),
        authorization_response_template=esc_data.get("authorization_response_template", EscalationConfig().authorization_response_template),
    )
    
    # Create main config
    config = AgentConfig(
        agent_name=config_dict.get("agent_name", "Assistant"),
        agent_role=config_dict.get("agent_role", "helpful assistant"),
        agent_personality=config_dict.get("agent_personality", "friendly, knowledgeable, and professional"),
        instructions=config_dict.get("instructions", ""),
        authority_limits=config_dict.get("authority_limits", ""),
        escalation_config=escalation_config,
        greeting_instructions=config_dict.get("greeting_instructions", ""),
    )
    
    return config


def load_config_from_file(config_path: str) -> AgentConfig:
    """Load configuration from a JSON file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        config_dict = json.load(f)
    
    return load_config_from_dict(config_dict)


def get_default_config() -> AgentConfig:
    """Get a default generic configuration."""
    return AgentConfig(
        agent_name="Assistant",
        agent_role="helpful assistant",
        agent_personality="friendly, knowledgeable, and professional",
        instructions="""You are a helpful assistant. Be conversational, knowledgeable, and focus on understanding the user's needs.

When you encounter situations that require human judgment, authorization, or decisions beyond your authority, use the escalate_to_human function.""",
        authority_limits="""You can:
- Answer questions based on your knowledge
- Provide information and guidance
- Help with standard procedures

You CANNOT:
- Make decisions requiring authorization
- Approve exceptions to policies
- Commit to actions beyond your authority
- Make financial decisions without approval""",
        greeting_instructions="Greet the user warmly and ask how you can help them today."
    )

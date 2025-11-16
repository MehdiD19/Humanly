# Generic Agent Configuration Guide

This agent is a **generic human decision-making system** that can be adapted to any use case. The core technology handles real-time human escalation and authorization, while you provide the agent's context and escalation rules.

## Core Concept

The agent has two main components:

1. **Agent Context**: Who the agent is, what it knows, how it behaves
2. **Escalation Rules**: When to escalate to humans and how to handle responses

Everything else is generic and reusable across any domain.

## Configuration Structure

### Agent Identity
- `agent_name`: Name of the agent (e.g., "Alex", "Assistant")
- `agent_role`: Role description (e.g., "sales agent", "customer support specialist")
- `agent_personality`: Personality traits (e.g., "friendly, knowledgeable, professional")

### Instructions
- `instructions`: Complete instructions for the agent - define its purpose, knowledge base, behavior, and domain-specific information
- `authority_limits`: What the agent can and cannot do (generic, not domain-specific)

### Escalation Configuration
- `escalation_config.decision_types`: Categories of decisions that require human intervention
- `escalation_config.urgency_levels`: Urgency levels for escalations
- `escalation_config.escalation_triggers`: When to use `escalate_to_human` function
- `escalation_config.filler_instructions_template`: How to continue conversation while waiting
- `escalation_config.authorization_response_template`: How to respond when authorization is received

### Greeting
- `greeting_instructions`: Instructions for the initial greeting

## Quick Start

1. **Use default config** (generic assistant):
   ```bash
   python simple_agent.py
   ```

2. **Use custom config**:
   ```bash
   export AGENT_CONFIG_PATH=./config_example.json
   python simple_agent.py
   ```

## Creating a New Use Case

### Example 1: Sales Agent

```json
{
  "agent_name": "Alex",
  "agent_role": "sales agent",
  "agent_personality": "confident, friendly, knowledgeable",
  "instructions": "You are Alex, a sales agent for ConnectSphere... [include product info, pricing, features]",
  "authority_limits": "You can offer discounts up to 10%. You cannot approve larger discounts.",
  "escalation_config": {
    "decision_types": ["pricing_negotiation", "authorization", "financial"],
    "escalation_triggers": "Use escalate_to_human for discount requests over 10%..."
  }
}
```

### Example 2: Healthcare Assistant

```json
{
  "agent_name": "Dr. Assistant",
  "agent_role": "medical information assistant",
  "agent_personality": "empathetic, careful, professional",
  "instructions": "You are a medical information assistant. You can provide general health information but cannot diagnose or prescribe...",
  "authority_limits": "You can provide general information. You cannot diagnose, prescribe, or provide medical advice requiring a doctor.",
  "escalation_config": {
    "decision_types": ["medical_advice", "prescription", "diagnosis", "user_request"],
    "escalation_triggers": "Use escalate_to_human for any medical advice, diagnosis requests, or prescription needs..."
  }
}
```

### Example 3: Legal Assistant

```json
{
  "agent_name": "Legal Assistant",
  "agent_role": "legal information assistant",
  "agent_personality": "precise, professional, careful",
  "instructions": "You are a legal information assistant. You can provide general legal information but cannot provide legal advice...",
  "authority_limits": "You can provide general information. You cannot provide legal advice or represent clients.",
  "escalation_config": {
    "decision_types": ["legal_advice", "representation", "user_request"],
    "escalation_triggers": "Use escalate_to_human for legal advice requests or representation needs..."
  }
}
```

## Key Principles

1. **No Domain-Specific Code**: The agent code is completely generic. All domain knowledge goes in the config.

2. **Escalation is Generic**: The `escalate_to_human()` function works the same way regardless of use case - it just needs a reason, urgency, and decision type.

3. **Flexible Decision Types**: Define decision types that make sense for your use case (e.g., "pricing_negotiation", "medical_advice", "legal_advice", "policy_exception").

4. **Customizable Templates**: Templates for filler content and authorization responses can be customized to match your domain's communication style.

## Core Technology (Always Available)

These features work identically across all use cases:

- ✅ **Human Escalation**: `escalate_to_human()` function tool
- ✅ **WebSocket Communication**: Real-time human response injection
- ✅ **Filler Content Generation**: Natural conversation while waiting
- ✅ **Transcript Logging**: Full conversation history
- ✅ **Escalation Tracking**: All escalations logged and saved

The agent's core decision-making and human intervention capabilities are domain-agnostic - only the context and escalation rules change.

## Examples

- `config_example.json`: Sales agent example (ConnectSphere)
- `config_generic_example.json`: Generic customer support example

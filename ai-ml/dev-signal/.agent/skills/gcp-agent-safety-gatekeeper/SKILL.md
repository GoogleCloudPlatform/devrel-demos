---
name: gcp-agent-safety-gatekeeper
description: Implements the "Defense-in-Depth" integration pattern in Python (intercepting prompts, parsing filter results).
---

# gcp-agent-safety-gatekeeper

This skill implements the Python integration layer for Model Armor. Grounded in `security_blog.md`, it provides the `safety_util` functions needed to intercept prompts, sanitize them against your security policy, and handle safety triggers in your FastAPI backend.

## Usage

Ask Antigravity to:
- "Add a safety gatekeeper to my agent backend"
- "Implement Model Armor prompt sanitization in Python"
- "Create a safety utility to parse Model Armor findings"
- "Handle prompt injection errors in my FastAPI app"

## Integration Pattern

1. **Client Initialization**: Configures the `ModelArmorClient` with the correct regional endpoint.
2. **`safety_util.py`**: A robust parser that converts `SanitizeUserPromptResponse` into a list of human-readable security triggers (e.g., "Prompt Injection", "PII: Person names").
3. **Application Interception**: Logic to block or sanitize prompts before they reach the GenAI model or agent orchestrator.

## Boilerplate Implementation

Refer to `scripts/safety_util.py` for the core parsing logic.

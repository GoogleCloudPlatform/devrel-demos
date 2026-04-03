---
name: adk-memory-bank-initializer
description: Helps developers implement the long-term memory layer by providing the boilerplate code for the VertexAiMemoryBankService and the save_session_to_memory_callback.
---

# adk-memory-bank-initializer

This skill helps you integrate long-term persistence into your AI agent using the Vertex AI Memory Bank. It ensures your agent "remembers" user preferences across sessions.

## Usage

Ask Antigravity to:
- "Initialize the memory bank for my agent"
- "Add a persistence callback to my root agent"
- "Set up VertexAiMemoryBankService"

## Memory Integration Pattern

The integration involves:
1. **Service Initialization**: Setting up the `VertexAiMemoryBankService` with the correct project and location.
2. **Persistence Callback**: Implementing a defensive `save_session_to_memory_callback` that runs after every turn.
3. **Agent Configuration**: Passing the `memory_service` to the `Runner` or `App`.
4. **Tool Selection**: Using `LoadMemoryTool` and `PreloadMemoryTool` to manage context recall.

## Python Boilerplate

Refer to the included `scripts/memory_config.py` for the standard implementation pattern.

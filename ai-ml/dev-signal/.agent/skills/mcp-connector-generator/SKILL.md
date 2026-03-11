---
name: mcp-connector-generator
description: Scaffolds the McpToolset connection logic for standard servers (Reddit, Google Docs) or custom local Python scripts.
---

# mcp-connector-generator

This skill helps you connect your AI agent to external data and tools using the Model Context Protocol (MCP). It provides boilerplate for the three most common connection types seen in production.

## Usage

Ask Antigravity to:
- "Connect my agent to Reddit via MCP"
- "Add the Google Cloud Docs (Knowledge) toolset"
- "Create a connector for my local Nano Banana script"

## Connection Patterns

1. **Local Subprocess (stdio)**: Best for npm-based servers (like reddit-mcp) or local Python scripts. Injects secrets into the environment.
2. **Remote Endpoint (HTTP)**: Used for managed services like the Developer Knowledge MCP server. Pass API keys in headers.
3. **Local Script (uv run)**: Executes a specific entrypoint within a project folder.

## Python Boilerplate

Refer to the included `scripts/mcp_connectors.py` for the standard implementation of `get_reddit_mcp_toolset`, `get_dk_mcp_toolset`, and others.

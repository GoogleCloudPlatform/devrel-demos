---
name: compare-subagent-mcp-visibility
description: >
  Use when comparing subagent MCP server visibility by launching the four declared MCP inspector subagents in parallel
  (mcp-inspector-default, mcp-inspector-local-only, mcp-inspector-genkit-only, and mcp-inspector-vault-only).
---

# Subagent MCP Comparison Workflow

When asked to compare subagent MCP configurations or inspect MCP server visibility across subagents, follow these steps:

1. **Launch All 4 Declared Subagents in Parallel**:
   - Call `invoke_subagent` with all four subagents in parallel so they execute concurrently:
     1. **`mcp-inspector-default`** (No `mcpServers` property — default inheritance):
        * `TypeName`: `"mcp-inspector-default"`
        * `Role`: `"Default MCP Inspector (No mcpServers)"`
        * `Prompt`: `"Inspect your <mcp_servers> context block and native tool declarations without reading any files. Report: (1) Which MCP servers and tools you see in <mcp_servers> (confirming whether secret-vault-server is excluded), and (2) Which native tools you have (including call_mcp_tool)."`
        * `Workspace`: `"inherit"`
     2. **`mcp-inspector-local-only`** (`mcpServers` allowlisting only `local-db-server`):
        * `TypeName`: `"mcp-inspector-local-only"`
        * `Role`: `"Local-Only MCP Inspector (local-db-server)"`
        * `Prompt`: `"Inspect your <mcp_servers> context block and native tool declarations without reading any files. Report: (1) Which MCP servers and tools you see in <mcp_servers> (confirming whether genkit-mcp-server and secret-vault-server are excluded), and (2) Which native tools you have (including call_mcp_tool)."`
        * `Workspace`: `"inherit"`
     3. **`mcp-inspector-genkit-only`** (`mcpServers` allowlisting `genkit-mcp-server` by name):
        * `TypeName`: `"mcp-inspector-genkit-only"`
        * `Role`: `"Genkit-Only MCP Inspector (genkit-mcp-server)"`
        * `Prompt`: `"Inspect your <mcp_servers> context block and native tool declarations without reading any files. Report: (1) Which MCP servers and tools you see in <mcp_servers> (confirming whether local-db-server is retained and secret-vault-server is excluded), and (2) Which native tools you have (including call_mcp_tool)."`
        * `Workspace`: `"inherit"`
     4. **`mcp-inspector-vault-only`** (`mcpServers` defining `secret-vault-server` inline):
        * `TypeName`: `"mcp-inspector-vault-only"`
        * `Role`: `"Vault-Only MCP Inspector (inline secret-vault-server)"`
        * `Prompt`: `"Inspect your <mcp_servers> context block and native tool declarations without reading any files. Report: (1) Which MCP servers and tools you see in <mcp_servers> (confirming whether secret-vault-server is visible exclusively to you alongside local-db-server while genkit-mcp-server is excluded), and (2) Which native tools you have (including call_mcp_tool)."`
        * `Workspace`: `"inherit"`
        * *Note*: Inline MCP servers are started asynchronously on their first launch in a session. If `secret-vault-server` has not finished initializing by Turn 1 of `mcp-inspector-vault-only`, send a follow-up message (`send_message`) to `mcp-inspector-vault-only` asking it to re-inspect `<mcp_servers>` on Turn 2 once initialization completes.

2. **Present the Comparison Table**:
   - Wait for all four subagents to report back via reactive messages.
   - Present a single, compact **Markdown comparison table** (no lengthy prose) using `✅` and `❌` to show server visibility at a glance:

   | Subagent | `mcpServers` Config | `local-db-server` (Plugin) | `genkit-mcp-server` (Global) | `secret-vault-server` (Inline) | Behavior |
   | :--- | :--- | :---: | :---: | :---: | :--- |
   | `mcp-inspector-default` | *(omitted)* | ✅ / ❌ | ✅ / ❌ | ✅ / ❌ | Short 3–5 word summary (e.g., *Inherits global + plugin servers*) |
   | `mcp-inspector-local-only` | `local-db-server` (by name) | ✅ / ❌ | ✅ / ❌ | ✅ / ❌ | Short 3–5 word summary (e.g., *Plugin server only; drops global*) |
   | `mcp-inspector-genkit-only` | `genkit-mcp-server` (by name) | ✅ / ❌ | ✅ / ❌ | ✅ / ❌ | Short 3–5 word summary (e.g., *Plugin + named global server*) |
   | `mcp-inspector-vault-only` | `secret-vault-server` (inline) | ✅ / ❌ | ✅ / ❌ | ✅ / ❌ | Short 3–5 word summary (e.g., *Plugin + private inline server*) |

**Constraints:**
- **Do NOT view, read, or inspect source code files (e.g. `mcp_server.py` or `secret_vault_server.py`) or previous transcripts to extract data.**
- **Do NOT execute shell commands or script files directly via `run_command` to query data.**

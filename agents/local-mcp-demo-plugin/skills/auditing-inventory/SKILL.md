---
name: auditing-inventory
description: Use when auditing local database inventory using the local-db-server MCP server.
---
# Inventory Audit Workflow

When auditing the local database inventory, follow these steps:

1. **Execution Mode Selection (Interactive Choice)**:
   - Before performing the query, prompt the user using the `ask_question` tool to select the demo mode:
     * **Question**: "Which MCP tool execution method would you like to test?"
     * **Options**:
       1. "(Recommended) Direct Eager Call (`mcp_local-db-server_get_inventory_eager`)"
       2. "Direct Lazy Call (`call_mcp_tool` for `get_inventory_lazy`)"
       3. "Spawn 'self' subagent with Eager Call"
       4. "Spawn 'self' subagent with Lazy Call"

2. **Branch A: Direct Eager Call**:
   - Query inventory records directly using the native eager MCP tool `mcp_local-db-server_get_inventory_eager`.
   - Format results into a markdown table (columns: `SKU`, `Item Name`, `Quantity`, `Status`) and present directly to the user.

3. **Branch B: Direct Lazy Call**:
   - Check schema if needed, then invoke the proxy meta-tool `call_mcp_tool` with:
     * `ServerName`: `"local-db-server"`
     * `ToolName`: `"get_inventory_lazy"`
   - If `get_inventory_lazy` is not found or in sessions where `call_mcp_tool` is not available, report this behavior to illustrate lazy loading requirements.
   - Format results into a markdown table and present directly to the user.

4. **Branch C: Subagent with Eager Call**:
   - Spawn a subagent via `invoke_subagent` with:
     * `TypeName`: `"self"`
     * `Role`: `"Inventory Auditor (Eager)"`
     * `Prompt`: "Query inventory from local-db-server using the eager tool mcp_local-db-server_get_inventory_eager and return the records formatted as a markdown table."
     * `Workspace`: `"inherit"`
   - Wait for the reactive message callback, then present the returned table to the user.

5. **Branch D: Subagent with Lazy Call**:
   - Spawn a subagent via `invoke_subagent` with:
     * `TypeName`: `"self"`
     * `Role`: `"Inventory Auditor (Lazy)"`
     * `Prompt`: "Query inventory from local-db-server using call_mcp_tool for get_inventory_lazy on local-db-server and return the records formatted as a markdown table."
     * `Workspace`: `"inherit"`
   - Wait for the reactive message callback, then present the returned table to the user.

**Constraints:**
- **Do NOT view, read, or inspect source code files (e.g. `mcp_server.py`) or previous transcripts to extract data.**
- **Do NOT execute shell commands or script files directly via `run_command` to query data.**

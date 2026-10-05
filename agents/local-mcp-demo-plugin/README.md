# Agent Plugin: Eager vs. Lazy MCP Tools & Lifecycle Hook Governance

This plugin demonstrates portable Model Context Protocol (MCP) server integration, the architectural differences between **Eager** and **Lazy** MCP tool registration, subagent delegation with `self` dynamic process clones, and `PreToolUse` / `PostToolUse` lifecycle hook governance.

For full explaination of this agent plugin refer to the article [Agent Plugins: Should you eagerly or lazily load MCP tools?](https://www.linkedin.com/pulse/agent-plugins-should-you-eagerly-lazily-load-mcp-tools-james-o-reilly-fgkue)

---

## Directory Structure

```text
plugins/local-mcp-demo-plugin/
├── README.md
├── plugin.json             # Plugin manifest
├── mcp_config.json         # MCP server configuration
├── hooks.json              # Lifecycle hook configuration
├── scripts/
│   ├── mcp_server.py       # MCP server (JSON-RPC stdio)
│   └── audit_hook.py       # Tool logging hook handler
└── skills/
    └── auditing-inventory/
        └── SKILL.md        # Agent skill for DB access
```

---

## Installation

You can install this plugin either locally for a specific workspace or globally across all your workspaces.

The plugin folder lives in the repository at:
`https://github.com/GoogleCloudPlatform/devrel-demos/tree/main/agents/local-mcp-demo-plugin`

### Workspace installation

```bash
npx giget gh+git:GoogleCloudPlatform/devrel-demos/agents/local-mcp-demo-plugin .agents/plugins/local-mcp-demo-plugin
```

### Global installation

```bash
npx giget gh:GoogleCloudPlatform/devrel-demos/agents/local-mcp-demo-plugin ~/.gemini/config/plugins/local-mcp-demo-plugin
```

---

## Test the plugin

To trigger the tests, prompt:
```text
Retrieve the inventory from the local-db-server
```

Then choose one of the 4 choices:

1. Direct Eager Call
2. Direct Lazy Call
3. Spawn `self` Subagent with Eager Call
4. Spawn `self` Subagent with Lazy Call

---

## Verifying Audit Logs (`plugin_tool_audit.log`)

Every tool call (direct or subagent) is intercepted by `PreToolUse` and `PostToolUse` hooks configured in `hooks.json`.

```bash
tail -n 20 plugin_tool_audit.log
```

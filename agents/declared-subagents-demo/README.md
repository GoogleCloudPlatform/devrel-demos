# Agent Plugin Demo: Configuring Subagents to Use MCP Servers

For full explaination of this agent plugin refer to the article [Agent Plugins: How to scope and isolate MCP servers in subagents](https://www.linkedin.com/pulse/agent-plugins-how-scope-isolate-mcp-servers-subagents-james-o-reilly-fkjee)


This plugin is a reference implementation for configuring **Model Context Protocol (MCP)** servers and tools inside **Antigravity Subagents**. It demonstrates how plugin-bundled `mcp_config.json` servers and the `mcpServers` frontmatter property in `agents/*.md` interact across four side-by-side configurations:

1. **`mcp-inspector-default.md`**: Inherits **all** active global MCP servers plus the enclosing plugin's `local-db-server` by default.
2. **`mcp-inspector-local-only.md`**: Uses `mcpServers` to drop all global MCP servers so only the plugin's `local-db-server` is exposed.
3. **`mcp-inspector-genkit-only.md`**: Allowlists a named global MCP server while retaining the enclosing plugin's `local-db-server` and excluding unlisted global servers.
4. **`mcp-inspector-vault-only.md`**: Declares an **agent-private inline MCP server** (`secret-vault-server`) directly in frontmatter so `secret-vault-server` is available **only** to this subagent (hidden from the main agent and sibling subagents), retaining `local-db-server` while dropping global MCP servers.

---

## Directory Structure

```text
declared-subagents-demo/
├── README.md
├── plugin.json                           # Plugin manifest
├── mcp_config.json                       # Plugin-level MCP server
├── agents/
│   ├── mcp-inspector-default.md          # 1) Omitted mcpServers
│   ├── mcp-inspector-local-only.md       # 2) Drops global servers
│   ├── mcp-inspector-genkit-only.md      # 3) Allowlists global MCP
│   └── mcp-inspector-vault-only.md       # 4) Agent-private inline MCP
├── scripts/
│   ├── mcp_server.py                     # Plugin-wide stdio MCP
│   └── secret_vault_server.py            # Agent-private stdio MCP
└── skills/
    └── compare-subagent-mcp-visibility/
        └── SKILL.md                      # Launches all subagents
```

---

## How `mcpServers` Works in Declared Subagents (`agents/*.md`)

| Subagent File | Frontmatter `mcpServers` | `local-db-server` (Plugin) | `genkit-mcp-server` (Global) | `secret-vault-server` (Inline) | Behavior |
| :--- | :--- | :---: | :---: | :---: | :--- |
| [`mcp-inspector-default.md`](./agents/mcp-inspector-default.md) | *(Omitted)* | ✅ | ✅ | ❌ | **Default Inheritance**: Omitting `mcpServers` inherits all active global servers plus the enclosing plugin's `mcp_config.json` servers. |
| [`mcp-inspector-local-only.md`](./agents/mcp-inspector-local-only.md) | `- name: local-db-server` | ✅ | ❌ | ❌ | **Plugin Server Only**: Listing only `local-db-server` drops all global MCP servers (`genkit-mcp-server`). |
| [`mcp-inspector-genkit-only.md`](./agents/mcp-inspector-genkit-only.md) | `- name: genkit-mcp-server` | ✅ | ✅ | ❌ | **Plugin + Named Global**: Retains the enclosing plugin's `local-db-server` plus the allowlisted global `genkit-mcp-server`, excluding other global servers. |
| [`mcp-inspector-vault-only.md`](./agents/mcp-inspector-vault-only.md) | `- name: secret-vault-server` *(inline `command` + `args`)* | ✅ | ❌ | ✅ | **Plugin + Private Inline Server**: `secret-vault-server` is isolated strictly to this subagent (invisible to the main agent and sibling subagents) alongside `local-db-server`. |

---

## Testing the 4-Agent Parallel Comparison

Install or symlink this plugin at `~/.gemini/config/plugins/declared-subagents-demo`, enable `local-db-server` and `genkit-mcp-server`, and run the `compare-subagent-mcp-visibility` skill in Antigravity:

```text
Compare subagent MCP server visibility by launching the four declared MCP inspector subagents in parallel.
```

The main agent will spawn `mcp-inspector-default`, `mcp-inspector-local-only`, `mcp-inspector-genkit-only`, and `mcp-inspector-vault-only` concurrently and return a side-by-side comparison table proving how plugin, global, and agent-private inline MCP servers are scoped.

# Elevating Antigravity Agent Skills Series

The **Elevating Antigravity Agent Skills** series is a 5-part engineering guide authored by [James O'Reilly](https://www.linkedin.com/in/jamesor/) for developers looking to elevate their AI agent workflows with native tools.

---

## 📚 The 5-Part "Elevating Antigravity" Series

| Part | Agent Tools | Topic & Core Focus | Article |
| :--- | :--- | :--- | :--- |
| **1** | `ask_question` | **Interactive UI Workflows & State Hydration**<br>Embed native interactive UI modals directly into skill instructions. Includes round-trip state hydration via `user_prefs.json` and human-in-the-loop (HITL) alignment strategies. [`making-forms-demo`](./skills/making-forms-demo/SKILL.md) | [Link](https://www.linkedin.com/pulse/elevating-antigravity-agent-skills-interactive-ui-james-o-reilly-kz8fc/) |
| **2** | `generate_image` | **Automating Studio-Grade Mock Assets**<br>Couple structured prompt tokenization (camera/lighting/scene parameters) with `generate_image` to synthesize clean, consistent mock visual assets directly in artifact storage. [`generating-mock-images`](./skills/generating-mock-images/SKILL.md) | Coming soon |
| **3** | `define_subagent`, `invoke_subagent` | **Parallel Subagents & Workspace Branching**<br>Register custom subagent personas and dispatch concurrent background workers across isolated git workspace branches (`Workspace: "branch"`) to prevent context saturation and slash wall-clock latency. | Coming soon |
| **4** | `send_message` | **Real-Time Inter-Agent Messaging & Telemetry**<br>Equip subagents with mid-flight reporting capabilities via `send_message` to transform background execution into transparent event-driven pipelines with zero-polling reactive wakeups. | Coming soon |
| **5** | `manage_subagents` | **Subagent Fleet Governance & Circuit Breakers**<br>Implement process supervisor governance using `manage_subagents` (`list`, `kill`, `kill_all`) to audit running worker threads, prevent resource leaks, and enforce automated hard circuit breakers. | Coming soon |

---

## 🚀 How to Use These Skills in Antigravity

### 1. Installation
Copy any skill folder from `skills/` into your active workspace's `.agents/skills/` directory (or into your global configuration directory at `~/.gemini/config/skills/`).

### 2. Automatic Skill Discovery
Antigravity automatically indexes `SKILL.md` instruction files upon workspace startup. When your chat prompt aligns with the description in a skill's YAML frontmatter, the agent automatically loads the skill into context.

# Tenkai: Experimentation Framework for Testing Coding Agents

Tenkai is a powerful framework designed to evaluate and optimize AI coding agents. It provides a structured environment for running A/B tests on system prompts, tool availability, and agent configurations across various coding scenarios. It provides a structured environment for running A/B tests on system prompts, tool availability, and agent configurations across various coding scenarios.

## Overview

In the rapidly evolving landscape of agentic coding, selecting the right tools and providing the optimal context is critical. Tenkai helps developers:
- **Analyze Tool Selection:** See which tools agents prefer for different tasks.
- **Evaluate Prompt Strategies:** Test how system prompt variations impact performance and efficiency.
- **Measure Reliability:** Track success rates, timeouts, and tool accuracy with statistical rigor.
- **Optimize Efficiency:** Monitor token usage and duration across experiments.

While designed with the [Gemini CLI](https://github.com/google/gemini-cli) in mind, Tenkai's architecture is agent-agnostic. With minimal adaptations, it can be used to evaluate any headless coding agent.

## Getting Started

### Prerequisites

- [Go](https://golang.org/doc/install) (1.21+)
- [Gemini CLI](https://github.com/google/gemini-cli) (properly configured)

### Installation

For quick usage:
```bash
go install github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/cmd/tenkai@latest
```

Or build from source:
```bash
git clone https://github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai.git
cd tenkai
go build ./cmd/tenkai/main.go
```

### Running Your First Experiment

Use the included minimal example to verify your setup:
```bash
./tenkai -config studies/_example/config.yaml
```

## Dashboard (Frontend)

Tenkai includes a high-performance dashboard for managing experiments and visualizing results.

```bash
cd frontend
npm install
npm run dev
```
Available at `http://localhost:3000`.

## Using with Jules

[Jules](https://jules.google) can effectively orchestrate Tenkai to optimize overall agentic performance. You can instruct Jules to:
- "Initialize a Tenkai experiment using `studies/_example/config.yaml`."
- "Create a new coding scenario that tests the agent's ability to refactor legacy Java code."
- "Analyze the latest Tenkai run and suggest a better system prompt to improve success rates."

## Scenarios

### Creating a New Scenario
1. Create a directory in the global `templates/` (shared) or in a study's local `templates/` (specific).
2. Add a `PROMPT.md` describing the task.
3. (Optional) Add starter code/files in the same directory.

Tenkai will look for scenarios in the study's `templates/` directory first, then fallback to the global `templates/`.

## Configuration (YAML)

```yaml
name: "experiment_name"
repetitions: 10
max_concurrent: 5
timeout: "5m"

alternatives:
  - name: "control"
    command: "..."
    args: ["..."]
    system_prompt_file: "..." # Optional path to prompt md
    settings_path: "..."      # Optional path to settings.json

scenarios:
  - name: "scenario_name"      # Found in study or global templates/
```

## Statistical Validity

Tenkai uses **Welch's t-test** for duration/tokens and **Fisher's Exact Test** for success rates to provide p-values and significance flags (`*`, `**`).

---
> [!IMPORTANT]
> **Tenkai is not an officially supported Google product.**

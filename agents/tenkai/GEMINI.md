# Tenkai Project Overview (for AI Agents)

Tenkai is a Go-based framework for analyzing and evaluating Model-Centric Programming (MCP) tool usage by AI agents, specifically optimized for the Gemini CLI.

## Directory Structure

- `cmd/tenkai`: Main entryway. Orchestrates experiment execution.
- `studies/`: Self-contained experiment directories (configs, prompts, and results).
- `internal/`: Core logic.
    - `runner/`: Executes scenarios using chosen alternatives. handles workspace isolation.
    - `workspace/`: Manages file system isolation and policy setup for each run.
    - `report/`: Statistical analysis and Markdown report generation.
    - `metrics/`: Stream-JSON parser for Gemini CLI events.
- `templates/`: Base code for scenarios (e.g., `api_implementation`, `concurrency_debug`).
- `experiments/runs/`: Output directory for generated logs, traces, and reports.

## Core Concepts

### 1. Alternatives
Variations of agent configuration:
- Different models.
- Modified system prompts.
- Different MCP tool availability (via `settings.json`).
- Policy restrictions (via `.gemini/policies/*.toml`).

### 2. Scenarios
Specific coding tasks located in `templates/`. Each scenario contains a `PROMPT.md` and initial source code.

### 3. Workspaces
Temporary directories where scenarios are executed. The orchestrator ensures that each run is isolated.

## How to Add an Experiment

1. Create a configuration directory in `configs/`.
2. Define `config.yaml` specifying alternatives and scenarios.
3. (Optional) Create custom system prompts or setting files in the same directory.
4. Run: `go run ./cmd/tenkai/main.go -config configs/your-dir/config.yaml`

## Reporting and Analysis

Tenkai uses Welch's t-test for continuous variables (Duration, Tokens, Lint) and Fisher's Exact Test for success rates to determine statistical significance between alternatives.
Reports are generated in Markdown with clickable links to failure traces and tool usage summaries.

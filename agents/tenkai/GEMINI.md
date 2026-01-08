# Tenkai Project Overview (for AI Agents)

Tenkai is a Go-based Experimentation Framework to test different configurations of coding agents. It provides a structured environment for evaluating agent performance across various scenarios, optimized for the Gemini CLI.

## Directory Structure

- `./tenkai`: Main entryway (binary). Orchestrates experiment execution.
- `scenarios/`: Reusable coding tasks. Each subdirectory is a scenario containing a `scenario.yaml` and `PROMPT.md`.
- `experiments/`: Experiment data and templates.
    - `runs/`: Output directory for generated logs, traces, and artifacts.
    - `templates/`: Configuration templates (`config.yaml`) for defining experiments.
    - `tenkai.db`: SQLite database storing all run history and metrics.
- `internal/`: Core logic.
    - `runner/`: Manages process execution, timeout handling, and log streaming.
    - `workspace/`: Manages file system isolation and policy setup for each run.
    - `report/`: Statistical analysis and console report generation.
    - `parser/`: Stream-JSON parser for Gemini CLI events.
    - `db/`: Database access layer.
    - `server/`: HTTP API server for the frontend.
- `frontend/`: Next.js web dashboard for real-time monitoring and analysis.

## Core Domain Model

## Lifecycle Statuses

Tenkai distinguishes between the orchestration state of an execution and the specific reason for its outcome.

### 1. Experiment Status (Overall Study)
Represents the state of the orchestrator process.
- **`RUNNING`**: The experiment is active and worker routines are processing jobs.
- **`COMPLETED`**: All configured repetitions for all alternatives and scenarios have reached a terminal run status.
- **`ABORTED`**: The orchestrator was terminated (e.g., via `Ctrl+C` or a "Stop" signal from the UI). Any pending jobs are cancelled.

### 2. Run Status (Individual Repetition)
Represents the state of a single (Alternative + Scenario + Repetition) tuple.
- **`QUEUED`**: The initial state. The run is registered in the database before the task is submitted to the worker pool. It is waiting for an available concurrency slot.
- **`RUNNING`**: The task has been picked up by a worker, the isolated workspace is prepared, and the agent process is currently executing.
- **`COMPLETED`**: The execution has ended naturally or was terminated by the runner (e.g., timeout). This is the terminal state for any run that was allowed to finish.
- **`ABORTED`**: The run was cancelled by the orchestrator before it could reach the worker or finish execution (e.g., due to a global experiment abort).

### 3. Run Reasons (Outcome Details)
Applicable only when a Run is in the `COMPLETED` status.
- **`SUCCESS`**: The agent process exited normally and passed all validation rules (tests, lint, coverage).
- **`FAILED (VALIDATION)`**: The agent finished its task, but the resulting code failed one or more validation rules.
- **`FAILED (TIMEOUT)`**: The agent exceeded the maximum allowed duration and was forcefully killed by the runner.
- **`FAILED (LOOP)`**: The runner detected an infinite tool-call loop and terminated the process.
- **`FAILED (ERROR)`**: A system-level error occurred (e.g., workspace preparation failed, executable not found).

### 2. Alternatives
Variations of agent configuration:
- Different models (e.g., `gemini 2.5 flash`, `gemini 3.0 flash preview`).
- Modified system prompts (`SYSTEM.md`).
- Different MCP tool availability (via `settings.json`).
- Policy restrictions (via `.gemini/policies/*.toml`).

### 3. Scenarios
Specific coding tasks located in `scenarios/`. Each scenario is defined by:
- `scenario.yaml`: Metadata, validation rules, and asset copying instructions.
- `PROMPT.md`: The actual task description given to the agent.

## Architecture Principles

### Single Source of Truth
- **`run_events` (Table):** The absolute ground truth for all agent actions.
- **Streaming Ingestion:** The runner streams stdout/stderr from the agent process directly to `run_events` in real-time using `StdoutPipe`.
- **Derived State:**
    - `run_results` (Summary): Token counts, tool usage counts, and durations are calculated by querying `run_events` (via `db.GetRunMetrics`), NOT by parsing log files.
    - `experiment_summaries`: Aggregated stats for the dashboard are derived from `run_results` and updated on every run completion.

### Process Execution & Safety
- **Process Groups:** Agents run in their own process group (`Setpgid`).
- **Clean Termination:** On timeout or abort, the runner sends `SIGKILL` to the entire process group (`syscall.Kill(-pid)`), ensuring no zombie processes (like `npm run dev`) remain.
- **Input Handling:** Agents receive a clean EOF on `Stdin` (`strings.NewReader("")`) to prevent hanging on user input.

## How to Add an Experiment

1.  **Define Scenario:** Create a new directory in `scenarios/` with `scenario.yaml` and `PROMPT.md`.
2.  **Create Template:** Create a directory in `experiments/templates/` with a `config.yaml`.
3.  **Run:**
    *   **Web UI (Preferred):** Start the server with `tenkai --serve & (cd frontend && npm run dev)` and navigate to `http://localhost:3000`.
    *   **CLI:** Run `tenkai --config experiments/templates/<template>/config.yaml`.

## Reporting and Analysis

Tenkai uses the following statistical tests to evaluate alternatives:
- **Welch's t-test:** For continuous variables (Duration, Tokens, Lint Issues).
- **Fisher's Exact Test:** For success rates and timeout rates (categorical data).

Reports are generated in Markdown and available in the database and web UI, including clickable links to failure traces and tool usage summaries.

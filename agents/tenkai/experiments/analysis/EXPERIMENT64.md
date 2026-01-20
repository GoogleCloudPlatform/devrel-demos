# Experiment 64 Analysis: The Impact of Tool Specialization on Agent Performance

**Date:** January 18, 2026
**Scenario:** Create a "Hello World" MCP Server in Go
**Model:** Default (Gemini 2.5 Pro)

## Executive Summary

Experiment 64 compared four agent configurations to determine the optimal toolset for Go development tasks. The results provide strong evidence that **tool specialization** and **removing generic tools** significantly improve agent reliability and performance.

| Alternative | Success Rate | Avg Duration | Key Characteristic |
| :--- | :---: | :---: | :--- |
| **godoctor-advanced-no-core** | **83.3%** | **~118s** | Specialized tools ONLY (No generic shell/file tools). |
| **godoctor-advanced-safe-shell-v2** | 56.7% | ~172s | Same as above, but with a verbose/safe shell wrapper. |
| **default** (Control) | 40.0% | ~360s | Generic tools ONLY (`run_shell_command`, `write_file`). |
| **godoctor-advanced** | 20.0% | ~348s | "Kitchen Sink" (Generic + Specialized tools). |

---

## 1. The Winning Strategy: `godoctor-advanced-no-core`

This configuration removed all generic tools (like `run_shell_command`, `write_file`, `read_file`) and forced the agent to use the specialized `godoctor` toolset (`go_build`, `go_test`, `file_edit`, `go_lint`).

### Why it worked (The "Happy Path")
Successful agents adopted a highly disciplined, iterative workflow:
1.  **Bootstrap:** `go_mod init` → `go_get` (MCP SDK).
2.  **Lint-Driven Development:** Agents used `go_lint` as a primary feedback loop. A common pattern was `file_edit` → `go_lint` → `file_edit` until the code was clean *before* attempting compilation.
3.  **Semantic Refactoring:** When `go_test` reported low coverage (typically 0-20% initially), agents in this group consistently **refactored** their code (extracting `newServer` logic) to make it testable, demonstrating a deep understanding of the codebase structure enabled by the tools.
4.  **Stability:** The atomic nature of `file_edit` (with fuzzy matching) proved far more reliable than overwriting entire files with `write_file`.

### Key Metrics
*   **Zero "Context Loss" Failures:** Unlike the control group, these agents rarely "lost" the file content because they modified it incrementally.
*   **High Tool Efficacy:** `file_edit` had a near-perfect success rate in applying changes.

---

## 2. The "Kitchen Sink" Failure: `godoctor-advanced`

This alternative provided *both* the generic core tools and the specialized Go tools. Counter-intuitively, it performed **worse** than the control group (20% vs 40%).

### Root Cause: Context Pollution & Choice Overload
*   **Tool Ignorance:** Despite having access to powerful tools like `go_test` and `go_lint`, the agent **ignored them** in 93% of runs.
    *   `run_shell_command` usage: **629 calls**
    *   `safe_shell` (Godoctor) usage: **0 calls**
    *   `go_test` usage: **~4 calls** (across all 30 runs!)
*   **Strategic Degradation:** The presence of ~20 extra, unused tools in the system prompt likely diluted the model's attention. The agent dithered, switching between `write_file` and `run_shell_command` chaotically, often getting stuck in loops where it would rewrite the same file repeatedly without making progress.
*   **Conclusion:** Providing "more tools" is harmful if they overlap with familiar, generic ones. The agent defaults to the path of least resistance (generic tools) but suffers from the noise of the unused tools.

---

## 3. The Control Group: `default`

The control group relied entirely on `run_shell_command` and `write_file`.

### Failure Modes
*   **API Hallucination Loops:** Without specialized knowledge or introspection tools, the agent frequently guessed incorrect APIs for the MCP SDK (e.g., `mcp.WithTool`, `transport.NewStdio`). It would spend 20+ turns attempting to compile, failing, and guessing again.
*   **Test Friction:** Testing a blocking server was a major hurdle. Agents tried complex `io.Pipe` and `goroutine` setups via `write_file` that often deadlocked or failed to synchronize, leading to timeouts.
*   **Brittle Edits:** Using `write_file` to fix small typos meant rewriting the entire file, which increased token usage and risk of hallucinations.

---

## 4. The "V2 Shell" Insight: `safe-shell-v2`

This alternative was identical to the winner (`no-core`) but used a newer version of the `safe_shell` tool.

### The "Stdin Trap"
The drop in performance (83% -> 57%) was primarily driven by a specific interaction loop:
1.  The agent tried to signal completion using `echo` piped to stdin: `{"command": "echo", "stdin": "Done"}`.
2.  `echo` ignores stdin. The output was empty.
3.  The agent interpreted empty output as failure and **retried the same command** infinitely (or until timeout).
4.  **Root Cause:** The V2 shell's verbose/structured output (`Command: ... Status: ...`) likely confused the agent or made it more sensitive to "empty" results compared to the V1 shell.

---

## 🚀 Recommendations

### For Tool Developers
1.  **Enforce Specialization:** When deploying specialized agents (e.g., for Go, Python, K8s), **disable the generic Core tools**. Force the agent to use the high-level abstractions designed for the domain.
2.  **Fix "Stdin Traps":** Tools wrapping shell commands should detect common pitfalls (like piping to `echo`) and warn the agent or auto-correct.
3.  **Documentation is Key:** The `no-core` agents succeeded because they effectively used `go_doc` (or had internalized knowledge) when forced to focus. Providing a "Testing Recipe" tool or guide for common patterns (like testing blocking servers) would save significant tokens.

### For Agent Design
1.  **Less is More:** Do not dump every available tool into the context. Curate the toolkit to the specific task.
2.  **Linting as a Gatekeeper:** The success of `no-core` suggests that forcing a "Lint -> Edit" loop before testing is a highly effective strategy for code generation agents.

# Experiment Analysis: GoDoctor vs Core Tools (Exp 72)

**Analyst:** Experiment Analyst Agent
**Date:** 2026-01-19
**Experiment ID:** 72 (`godoctor_mcp_server_001`)

## Executive Summary

This experiment compared the effectiveness of the **GoDoctor** MCP server against the base Gemini CLI (`core` tools) for Go development tasks.

*   **Winner:** `godoctor-no-core` (Specialized tools only).
*   **Key Finding:** **Less is More.** Removing generic tools (`run_shell_command`, `read_file`) and forcing the agent to use specialized GoDoctor tools reduced duration by **40%** and token usage by **23%** while maintaining a high success rate (80%).
*   **Problem:** The full `godoctor` configuration (Core + GoDoctor) suffered from **Context Pollution**. The agent defaulted to inefficient shell commands instead of using the powerful specialized tools available to it, leading to bloated sessions and higher costs.

## metrics Overview

| Alternative | Success Rate | Avg Duration | Avg Tokens | Efficiency Score |
| :--- | :--- | :--- | :--- | :--- |
| **godoctor-no-core** | **80%** (24/30) | **122s** | **555k** | 🟢 High |
| **default** (Base) | 80% (24/30) | 202s | 725k | 🟡 Medium |
| **godoctor** (All) | 76% (23/30) | 208s | 998k | 🔴 Low |

*   `godoctor-no-core` was **1.7x faster** than the default agent.
*   `godoctor` (All tools) consumed **37% more tokens** than the default agent for worse performance.

## Deep Dive: Workflow Analysis

### The "Bloated" Path (`godoctor` - All Tools)
*   **Behavior:** The agent ignored `go_test`, `go_build`, and `file_edit` in favor of `run_shell_command`.
*   **Observed Pattern:**
    1.  `run_shell_command("go test ...")`
    2.  Agent manually parses stdout.
    3.  `run_shell_command("go build ...")`
    4.  Agent manually parses errors.
    5.  `write_file` (overwriting entire files instead of patching).
*   **Consequence:** This "manual" loop is extremely verbose. The agent spent 45+ steps fighting with shell output parsing and re-reading files, leading to massive token consumption.

### The "Optimized" Path (`godoctor-no-core`)
*   **Behavior:** Forced to use specialized tools.
*   **Observed Pattern:**
    1.  `file_create` / `file_edit` -> **GoDoctor automatically handles formatting and imports.** (No separate `go fmt` shell calls needed).
    2.  `go_test` -> **GoDoctor returns structured JSON/Markdown.** (No manual parsing of stdout needed).
    3.  `safe_shell` -> Used sparingly for init/get.
*   **Consequence:** The workflow is streamlined. The agent creates, tests (getting clear feedback), and fixes in tight loops.

### Deep Dive: Hybrid Workflow Analysis (The "Mixed" Runs)
A deeper look at the `godoctor` alternative reveals that the agent *did* occasionally use specialized tools, but failed to commit to a pure workflow.

*   **Prevalence:** 100% of `godoctor` runs were "Mixed Usage".
*   **Most Popular Tool:** `go_docs` was widely used (likely because `run_shell_command` has no easy equivalent).
*   **Inefficient Interleaving (Run 4434 - Success, 188s):**
    *   The agent used `go_get` and `go_docs` effectively at the start.
    *   However, it fell back to a loop of `run_shell_command` -> `file_edit` -> `run_shell_command`.
    *   **Missed Opportunity:** Instead of using `go_test` (which parses output), it ran `go test` via shell and manually parsed the text logs, wasting tokens and turns.
*   **Context Switching Costs (Run 4389 - Failed, 425s):**
    *   The agent tried `go_build`, then immediately reverted to `run_shell_command`.
    *   This inconsistency suggests the agent treats specialized tools as "novelties" rather than the primary interface, leading to cognitive thrashing and eventual timeouts.

## Root Cause Analysis

**1. Choice Overload (Context Pollution)**
In the `godoctor` alternative, the agent had access to both `run_shell_command` and `go_test`. It consistently chose `run_shell_command`. This suggests the model has a strong bias towards generic tools it "knows" well from training, even when better tools are available in the context.

**2. Tool Superiority (GoDoctor)**
GoDoctor's tools provide higher-order value:
*   `file_edit`: Auto-fixes imports/formatting, saving at least 2 turns per edit.
*   `go_test`: Summarizes coverage and errors, saving parsing tokens.

## Failure Analysis

We analyzed the failed runs to identify common failure modes:

*   **Context Pollution / Infinite Loops (Run 4380 - godoctor):**
    *   This run consumed **2.3 MILLION tokens** and lasted 418 seconds.
    *   The agent got stuck in a loop of `run_shell_command` -> `replace` -> `run_shell_command`, trying to manually fix compilation errors that `file_edit` (with its auto-fix capabilities) would have handled in one step. It eventually timed out or was killed.
*   **Strategy Failure / "Lazy Agent" (Run 4378 - godoctor-no-core):**
    *   The agent executed `file_list`, stated "I will initialize the Go module...", and then **stopped** without calling any further tools.
    *   This suggests that without the familiar `run_shell_command` crutch, the agent occasionally fails to formulate a plan using the new tools (`safe_shell`) or hallucinates completion.
*   **System Instability (Run 4369):**
    *   Some failures were due to underlying infrastructure crashes (Node.js/Gemini CLI errors), independent of agent behavior.

## Trend Analysis (Comparison with Previous Experiments)

We compared the best performing alternative in this experiment (`godoctor-no-core`) against the best performers from previous experiments (Exp 67 and Exp 68).

| Experiment | Best Alternative | Success Rate | Avg Duration | Avg Tokens | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Exp 72 (Current)** | `godoctor-no-core` | **80%** | **122s** | **555k** | 🚀 **State of the Art** |
| Exp 68 | `advanced-no-core-v2` | 67% | 178s | 525k | Faster but less reliable |
| Exp 67 | `standard-no-core-v2` | 73% | 277s | 866k | Reliable but slow |

**Conclusion:**
Experiment 72 represents a significant leap forward.
1.  **Reliability:** It achieved the highest success rate (80%) seen in this series.
2.  **Speed:** It is **55% faster** than the reliable baseline (Exp 67) and **30% faster** than the previous speed champion (Exp 68).
3.  **Optimization:** The combination of *Specialized Tools Only* (No Core) + *Safe Shell Integration* has proven to be the optimal configuration for Go development tasks.

## Recommendations

1.  **Policy Update:** For specialized domains (like Go dev), **disable generic tools**. Do not give the agent `run_shell_command` if `safe_shell` or `go_build` exists. The agent cannot reliably self-regulate its tool choice.
2.  **Prompt Engineering:** If generic tools *must* remain, the System Prompt needs explicit instruction: *"ALWAYS prefer `go_test` over running `go test` in the shell."*
3.  **Adoption:** Promote `godoctor-no-core` as the standard profile for Go development tasks.

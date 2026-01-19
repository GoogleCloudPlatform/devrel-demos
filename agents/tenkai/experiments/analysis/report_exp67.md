# Experiment 67 Analysis: GoDoctor vs Safe Shell Variants

## Executive Summary
Experiment 67 evaluated the impact of toolset variations on a Go coding task (building an MCP server). The primary goal was to compare the standard "GoDoctor" toolset against "No Core" variants, specifically testing a new "Safe Shell v2" configuration.

**Winner:** `godoctor-standard-no-core-safe-shell-v2` tied with `default` for the highest success rate (**73%**) but was significantly more efficient, completing tasks **~20% faster** (277s vs 345s) with slightly lower token usage.

**Loser:** `godoctor-standard-no-core` performed poorly with only a **36%** success rate, highlighting the critical importance of the improved shell capabilities for this type of task.

## Comparative Analysis

| Alternative | Success Rate | Avg Duration | Avg Tokens |
| :--- | :--- | :--- | :--- |
| **Safe Shell v2** | **73.3%** (22/30) | **277s** | 866k |
| Default | 73.3% (22/30) | 345s | 905k |
| Standard | 66.7% (20/30) | 343s | 1.08M |
| No Core | 36.7% (11/30) | 127s | 392k |

### Workflow Contrast

*   **Happy Path (Safe Shell v2):**
    1.  **Discovery:** Identifies correct SDK (`modelcontextprotocol/go-sdk`).
    2.  **Implementation:** Creates `main.go` and `main_test.go`.
    3.  **Refinement:** Tight loop of `go_test` -> `go_lint` -> `file_edit`.
    4.  **Verification:** Uses `safe_shell` to pipe JSON-RPC commands to the compiled binary (`./hello`), confirming `stdio` transport works.
    5.  **Completion:** Explicitly validates output before finishing.

*   **Failure Mode (No Core):**
    1.  **Hallucination:** Frequently attempts to use incorrect/community SDKs (`mark3labs/mcp-go`) and gets stuck trying to make them work.
    2.  **Verification Gap:** Lacks a robust pattern for manual verification. Often skips the final `safe_shell` integration test or fails to configure it correctly (e.g., handling timeouts/hanging processes), leading to task failure.
    3.  **Edit Loops:** Gets stuck in `file_edit` -> `file_edit` cycles, unable to resolve linter or compiler errors effectively.

## Root Causes

1.  **Verification Capability (Critical):** The `safe-shell-v2` alternative enables the agent to perform **Black-Box Integration Testing**. By successfully running the compiled binary and interacting with it via `stdin/stdout`, the agent can definitively verify the acceptance criteria. The `no-core` variant struggled to construct or execute these tests, leading to "false positives" (thinking it was done when code was broken) or "give ups".

2.  **SDK Grounding:** A significant source of friction was the agent selecting the wrong SDK (`mark3labs` vs `modelcontextprotocol`).
    *   *Evidence:* Failed runs show repeated `go_get` calls for the wrong package.
    *   *Impact:* This wasted time and tokens. The `safe-shell-v2` agent often recovered from this by failing the verification step and searching again, whereas the `no-core` agent just failed.

## Recommendations

1.  **Standardize Safe Shell v2:** The v2 configuration provides a clear performance and reliability boost. It should be promoted to the default `godoctor` profile.
2.  **Enhance Discovery Tools:** To fix the SDK hallucination issue, explicitly encourage or tool the agent to `search` or `go_docs` *before* `go_get` when the package name isn't provided.
3.  **Verification Pattern:** The "Build -> Pipe JSON -> Verify Output" pattern is a strong indicator of success for CLI/MCP tasks. Consider adding this as a specific "recipe" or few-shot example in the system prompt.

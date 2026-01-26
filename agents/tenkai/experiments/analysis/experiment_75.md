# Experiment 75 Analysis: GoDoctor Effectiveness

**Experiment ID:** 75
**Name:** `godoctor_mcp_server_004`
**Objective:** Compare standard Gemini CLI against a configuration enhanced with the `godoctor` MCP server for Go program development.

## 📊 Performance Overview

| Metric | Default (Control) | GoDoctor (Treatment) | Delta |
| :--- | :--- | :--- | :--- |
| **Success Rate** | 44% (22/50) | **58% (29/50)** | **+14%** |
| **Avg Duration** | 278.0s | **181.4s** | **-35%** |
| **Avg Tokens** | 833.8k | 949.7k | +14% |

## 🛠 Tool Usage Analysis

### Overall Tool Reliability
| Alternative | Total Calls | Failed Calls | Failure Rate |
| :--- | :--- | :--- | :--- |
| **Default** | 1747 | 41 | 2.35% |
| **GoDoctor** | 1321 | 29 | 2.20% |

> **Note:** "Failed Calls" includes logical failures (e.g., build errors returning non-zero exit codes) which are tracked by the runner. The detailed breakdown below shows usage counts only.

### Default (Control)
| Tool Name | Total Calls |
| :--- | :--- |
| `run_shell_command` | 1000 |
| `write_file` | 434 |
| `replace` | 182 |
| `read_file` | 45 |
| `google_web_search` | 26 |
| `list_directory` | 16 |
| `web_fetch` | 3 |

### GoDoctor (Treatment)
| Tool Name | Total Calls |
| :--- | :--- |
| `run_shell_command` | 657 |
| `write_file` | 286 |
| `file_create` | 80 |
| `replace` | 79 |
| `smart_edit` | 69 |
| `read_docs` | 55 |
| `read_file` | 21 |
| `add_dependency` | 16 |
| `verify_tests` | 12 |
| `verify_build` | 6 |
| `list_directory` | 6 |
| `list_files` | 4 |
| `google_web_search` | 1 |

## 🔍 Workflow Analysis

### 1. Default Alternative (Brute Force)
The `default` agent operated in a "guess-verify-fix" loop. Without the ability to inspect package documentation directly, it relied on:
*   **Hallucination:** Repeatedly attempting to use methods like `server.ServeStdio()` (which were invalid for the SDK version).
*   **Manual Inspection:** Wasting time and tokens on `ls -R` and `cat` commands to explore the filesystem in `pkg/mod`.
*   **Replacement Churn:** Brittle string replacements led to frequent syntax errors, evidenced by 128 `replace` -> `run_shell_command` transitions.

### 2. GoDoctor Alternative (Informed)
The `godoctor` agent followed a structured, documentation-first approach:
*   **Contextual Awareness:** Used `read_docs` (34 total calls) to understand the `modelcontextprotocol/go-sdk` API before writing code.
*   **Reliable Implementation:** Leveraged `file_create` and `smart_edit` to implement the "Happy Path" (e.g., `server.Run`) on the first try.
*   **Validation:** Used `verify_tests` and `verify_build` to catch errors early, reducing the time spent in broken build states.

## 📉 Validation Failure Analysis

Both alternatives faced significant challenges in meeting the strict **50% code coverage requirement**, which was the primary determinant of failure for runs that otherwise produced functional code.

### Failure Reasons
| Alternative | FAILED (VALIDATION) | FAILED (TIMEOUT) |
| :--- | :--- | :--- |
| **default** | 23 | 5 |
| **godoctor** | 21 | 0 |

### The Coverage Trap
While agents frequently wrote passing tests (e.g., `PASS: TestHelloWorld`, `PASS: TestRun`), they consistently failed to achieve the 50% coverage threshold across the entire module.
*   **Near Misses:** Many runs achieved **40-48% coverage**, narrowly missing the target.
*   **Untested Clients:** A common pattern was thorough testing of the `server` package but neglect of the `client` package (often 0% coverage), dragging down the total score.
*   **Timeouts:** The `default` agent suffered 5 timeouts, likely due to the time-consuming "guess-and-check" loops identified in the workflow analysis. `godoctor` had zero timeouts, reinforcing its efficiency advantage.

### Coverage Threshold Recommendation
An analysis of functional runs (passing tests but failing coverage) suggests the current **50% threshold is too aggressive** for this scenario, where client code is often left untested.

| Threshold | Additional Successes | Total Impact |
| :--- | :--- | :--- |
| **45%** | +10 Runs | Captures the "Near Miss" cluster (45-49%). |
| **40%** | +18 Runs | Captures widely partial tests, but risks lower quality. |

**Recommendation:** Lowering the validation standard to **45%** would have increased the valid yield by **~20%** without significantly compromising the verification of core logic.

## 💡 Root Causes

### Why GoDoctor Won
The primary driver of success was **Grounding**. By having access to the source documentation via `read_docs`, the agent eliminated the trial-and-error cycle inherent in working with unfamiliar or evolving APIs. Although this increased token consumption slightly, it drastically improved velocity and reliability.

### Why Default Struggled
The `default` agent was trapped in **Strategy Failure**. It attempted to implement logic based on general knowledge of MCP, which didn't match the specific version of the Go SDK installed. Its only recovery mechanism was to guess or manually grep through files, both of which are slow and prone to failure.

## 🛠 Recommendations

1.  **Promote Semantic Editing:** Standardize the use of `smart_edit` over generic `replace` to minimize build breakage.
2.  **Optimize Documentation Retrieval:** `read_docs` is highly effective but expensive. Implementing a "structural outline" mode could provide the necessary signatures at a lower token cost.
3.  **Default Dependency Grounding:** For any task involving a `go get` or `go get -u`, the agent should be prompted to immediately run `read_docs` on the new dependency.

---
*Report generated by Gemini Experiment Analyst.*

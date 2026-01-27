# Experiment 99: godoctor_vs_gopls_002

**Overview**
This experiment evaluates the performance of the **Godoctor** extension (v0.11.0) against `gopls-mcp` and a `default` baseline in a scenario involving multi-package Go project initialization and dependency management.

**Results Summary**
| Alternative | Success Rate | Avg Duration (s) | Avg Tokens | Key Characteristic |
|---|---|---|---|---|
| **godoctor-extension** | **90% (45/50)** | **160.8s** | 1.6M | High adoption of specialized tools |
| **gopls-mcp** | 80% (40/50) | 242.3s | 1.5M | Baseline with gopls integration |
| **default** | 76% (38/50) | 228.8s | 1.4M | Reliance on raw shell commands |

**Key Findings**

1.  **Superior Efficiency:**
    The `godoctor-extension` is significantly faster than both alternatives, completing tasks ~80 seconds faster than `gopls-mcp` (34% reduction in duration). This is attributed to the "one-stop-shop" nature of tools like `project_init` and `add_dependency`.

2.  **Resilience to Hallucination:**
    The documentation fallback logic in `add_dependency` and `project_init` proved to be a critical success determinant.
    *   *Evidence:* In multiple runs (e.g., Run 6028), when the model attempted to install versioned or non-existent sub-packages, the tool returned documentation for the module root and a list of valid sub-packages. This allowed the agent to self-correct in the very next turn without getting stuck in a retry loop.

3.  **Verification as a Quality Gate:**
    `smart_build` (used in 13% of successful runs) acted as an effective safety net. Successful runs using `smart_build` achieved 100% verification on the first attempt, as the tool enforces formatting and linting rules that raw shell commands often skip.

4.  **Error Recovery Patterns:**
    The strong negative correlation between `smart_read` usage and success (-47%) is a **lagging indicator**, not a root cause.
    *   *Analysis:* Perfect "One-Shot" runs (47% of successes) rarely need to read files. Runs that encounter errors (100% of failures + 53% of successes) use `smart_read` to diagnose and fix them. Thus, `smart_read` is correctly functioning as a recovery tool for non-ideal paths.

**Deep Dive: The "Godoctor Flow"**
Reconstructing the workflows (via `analyze_patterns.py`) revealed a highly optimized cognitive pattern exclusive to the `godoctor-extension` alternative:

1.  **Standardized Scaffolding:** 86% of runs (43/50) started with `project_init`, immediately establishing a clean module structure.
2.  **Knowledge Injection:** The `project_init` -> `add_dependency` transition (seen in 21 runs) ensures that the agent has both the library code and its documentation in-context before writing a single line of application logic.
3.  **Low-Friction Implementation:** Transitioning from `file_create` to `smart_edit` for refactoring (seen in 70 instances) allowed agents to move logic into sub-packages with 0% syntax error rate, compared to a ~15% failure rate for agents using raw `replace` in the baseline.

**Conclusion & Recommendations**
*   **Winner:** `godoctor-extension` is the clear winner for Go-specific agentic tasks.
*   **Recommendation:** Maintain the "Hinting on Failure" logic in all GoDoctor tools. It effectively turns model errors into successful outcomes by providing the missing context needed for self-correction.
*   **Action Item:** Ensure `smart_read` remains easily accessible as the primary debugging tool. Discouraging its use would likely harm success rates by removing the agent's ability to recover from "imperfect" generations.

# Experiment 68 Analysis: Advanced Prompt & Safe Shell v2

## Executive Summary
Experiment 68 investigated the impact of an **"Advanced" System Prompt** combined with the **Safe Shell v2** toolset. The goal was to see if a more directive prompt could improve performance or efficiency compared to the standard prompt used in Experiment 67.

**Winner:** `godoctor-advanced-no-core-safe-shell-v2` was the most efficient, reducing duration by **~50%** (178s vs 377s) compared to the default, while maintaining a competitive success rate (**67%**).

**Insight:** The "Advanced" prompt significantly accelerates the workflow by guiding the agent to the correct solution faster, but the `safe-shell-v2` remains the critical enabler for verification. Without the shell (in `no-core`), success dropped to **47%**.

## Comparative Analysis

| Alternative | Success Rate | Avg Duration | Avg Tokens |
| :--- | :--- | :--- | :--- |
| **Advanced + Safe Shell v2** | **67%** (20/30) | **178s** | 525k |
| Default | 73% (22/30) | 377s | 1.02M |
| Advanced (Full) | 73% (22/30) | 391s | 979k |
| Advanced (No Core) | 47% (14/30) | 145s | 489k |

### Efficiency vs. Reliability
*   **Speed:** The `Advanced + Safe Shell v2` variant is **~100 seconds faster** than the `Standard + Safe Shell v2` from Exp 67 (277s -> 178s).
*   **Reliability:** However, the success rate dropped slightly (73% -> 67%). The "Advanced" prompt might encourage "rushing," leading to minor errors that the rigorous verification of the "Standard" prompt catches.

### Workflow Patterns
*   **Streamlined Execution:** The successful agents in this experiment followed a very tight script: `Init` -> `Create` -> `Test` -> `Build` -> `Verify`. There was significantly less "wandering" or "exploring" (e.g., fewer `go_docs` calls) compared to Experiment 67.
*   **Verification is Key:** Just like in Exp 67, the ability to run `./hello` and pipe JSON-RPC via `safe_shell` was the deciding factor. The `no-core` variants failed because they couldn't reliably perform this black-box integration test.

## Root Causes
1.  **Prompt Efficiency:** The "Advanced" prompt successfully reduced cognitive load, leading to lower token usage and faster execution. It likely contained more specific instructions on *how* to implement the server, reducing the need for `go_docs`.
2.  **Verification Fragility:** The drop in success rate (vs Exp 67) suggests that while faster, the "Advanced" agent might be skipping some safety checks. The logs show fewer "self-corrections" – if the first attempt failed verification, the agent sometimes struggled to recover or gave up, whereas the "Standard" agent was more persistent.

## Recommendations
1.  **Adopt Advanced Prompt for Speed:** For time-critical tasks, the "Advanced" prompt is superior.
2.  **Enforce Verification:** To mitigate the slight reliability drop, the System Prompt should explicitly mandate a "Verification Phase" (as seen in the successful runs) to prevent the agent from submitting unverified code.
3.  **Standardize Safe Shell v2:** This experiment re-confirms that `safe-shell-v2` is essential for CLI tool development tasks. It should be the default.

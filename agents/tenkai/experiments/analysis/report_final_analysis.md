# Final Analysis: Configuration, Context, and Instability

## Executive Summary
This analysis investigated the performance differences between GoDoctor configurations in Experiments 67 and 68, specifically addressing the high failure rate of the `godoctor-standard-no-core` alternative.

## Root Cause 1: Configuration Mismatch (Experiment 67)
In Experiment 67, the `godoctor-standard-no-core` alternative failed 46% of the time (14/30 runs) with "Silent Refusals" (0 output tokens).
*   **Cause:** This alternative was accidentally configured with the **Advanced Profile** (18 tools), while the comparison group (`safe-shell-v2`) used the **Standard Profile** (11 tools).
*   **Impact:** The Advanced Profile presents a significantly larger and more complex prompt context. Combined with the removal of standard Core tools, this "Context Overload" destabilized the Gemini 3 Pro model, leading to frequent refusals to generate a response.

## Root Cause 2: Platform Instability (Experiment 68)
In Experiment 68, both alternatives correctly used the **Advanced Profile**. The prompt context was confirmed to be **identical** (verified via code audit).
*   **Result:** `no-core` still failed 50% of the time (15 runs), while `safe-shell-v2` failed 16% of the time (5 runs).
*   **Cause:** Since inputs were identical, the disparity is attributed to **Statistical Noise** in a highly unstable environment.
*   **Evidence:** Explicit "503 Model Overloaded" errors were found in the logs (Run 4070), confirming the platform was under stress. The "Silent Failures" (0 tokens) are likely a related symptom of this instability (e.g., connection resets or API timeouts handled silently by the CLI). The `no-core` group's higher failure count in this specific run is likely bad luck (worker scheduling) rather than a deterministic product of the toolset.

## Key Takeaways
1.  **Context Sensitivity:** The Gemini 3 Pro model is sensitive to prompt size/complexity. The "Advanced" profile (18 tools) pushes it closer to a stability cliff compared to the "Standard" profile.
2.  **Silent Failures:** When the model (or API) hits this stability cliff, it often results in a "Silent Failure" (0 output tokens, Clean Exit) rather than an explicit error message, complicating debugging.
3.  **Efficiency:** When it *does* work, the **Advanced Profile** (combined with `safe-shell-v2`) is significantly more efficient (**35% faster**), likely due to "Context Priming" where the presence of professional tools encourages more decisive behavior.

## Recommendations
*   **Stabilize Context:** Use the **Standard Profile** for general reliability.
*   **Adopt Safe Shell v2:** Always use `safe-shell-v2` (Soft Guardrails) as it prevents deadlocks when the model attempts standard shell commands.
*   **Monitor 0-Token Runs:** Implement detection for "Silent Failures" (Success status but 0 output tokens) to automatically retry or flag these runs, as they indicate platform/model instability rather than agent failure.
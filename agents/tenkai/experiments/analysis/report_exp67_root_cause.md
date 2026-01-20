# Deep Dive: The Invisible Hand of Configuration

## The Mystery
In Experiment 67, the `godoctor-standard-no-core` alternative failed 50% of the time with "Immediate Give-Up" (0 output tokens). The `godoctor-standard-no-core-safe-shell-v2` alternative, which seemingly only changed a boolean flag in the server, succeeded 73% of the time.

Critically, since the failures happened *before* any tool execution, the difference must be visible in the **Prompt/Context**.

## The Smoking Gun: Configuration Drift
A review of `instructions.go` confirms that the System Instructions are dynamically generated based on *enabled tools*. However, `safeShellV2` is passed to `run.Register` but **does not affect the `instructions.Get` output**. The instruction string for `cmd.run` is identical in `registry.go` regardless of the v2 flag.

**However, the Experiment 67 configuration reveals a critical mismatch:**

```yaml
    - name: godoctor-standard-no-core
      settings:
        mcpServers:
            godoctor:
                args:
                    - --profile=advanced  <-- !!! USES ADVANCED PROFILE
```

```yaml
    - name: godoctor-standard-no-core-safe-shell-v2
      settings:
        mcpServers:
            godoctor:
                args:
                    - --profile=standard  <-- !!! USES STANDARD PROFILE
                    - --safe-shell-v2
```

## The "Context Overload" Hypothesis
The `no-core` alternative wasn't just "Standard without Core". It was **"Advanced Profile without Core"**.

*   **Context A (No Core):** 18 Tools (including complex agents like `code_review`, `symbol_inspect`) + Long Instructions.
*   **Context B (Safe Shell v2):** 11 Tools (Basic) + Shorter Instructions.

**Conclusion:** The high failure rate in `godoctor-standard-no-core` was likely caused by **Context Overload/Instability**. The presence of 18 complex tool definitions (many of which, like `agent.specialist`, have lengthy instructions in `instructions.go`) combined with the "No Core" constraint pushed the Gemini 3 Pro model into an unstable state where it frequently refused to generate a response. The `safe-shell-v2` variant inadvertently "fixed" this by reverting to the simpler `Standard` profile in the config, reducing the context load.

## Correction for Exp 68
In Experiment 68, *both* alternatives correctly used `--profile=advanced`.
*   `no-core` (Advanced): 15 failures.
*   `no-core-safe-shell-v2` (Advanced): 5 failures.

Here, the variable IS isolated to `safe-shell-v2`. Since the text description is identical, the only difference is the **internal behavior** of the tool. But again, if it fails *before* execution, behavior doesn't matter.

**Re-evaluating Exp 68 Failures:**
*   Is it possible the 0-token runs in Exp 68 are just random noise?
*   Or did `safe-shell-v2` somehow change the prompt? **No.**
*   Did it change the *Tool Definition JSON schema*?
    *   `Handler` implementation changes, but `Register` uses `toolnames.Registry`.
    *   The `Registry` is static.

**Final Mystery:** In Exp 68, where profiles are identical, why does v2 still fail less (5 vs 15)?
*   **Possibility:** Random chance? (Small sample size 30).
*   **Possibility:** There is a subtle difference in the JSON schema I missed.
    *   `Params` struct tags: `jsonschema:"..."`.
    *   Does `validateCommandV2` logic affect the *schema*? No.

**Verdict:** The massive disparity in **Exp 67** (46% vs 10%) is explained by the **Profile Mismatch** (Advanced vs Standard). The disparity in **Exp 68** (50% vs 16%) is harder to explain if the prompt is truly identical. It implies either a hidden variable or significant stochasticity in how the model handles the "Advanced + No Core" context.

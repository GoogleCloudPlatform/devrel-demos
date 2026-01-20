# Deep Dive: The Efficiency Paradox

You asked for concrete scenarios where tool usage made the agent better or worse. My analysis uncovered a fascinating result: **The "Advanced" agent became better by doing *less*.**

Comparing representative successful runs from Experiment 67 (Standard Profile) and Experiment 68 (Advanced Profile) reveals a distinct shift in behavior.

## Scenario: The "Confidence" Gap

The critical difference wasn't which tools were *used*, but which were *skipped*.

### Standard Agent (Run 3928) - "The Anxious Verifier"
*   **Context:** Sees basic tools (`file_edit`, `go_test`, `safe_shell`).
*   **Behavior:** After implementing the code and passing unit tests, this agent didn't trust the result. It manually constructed an integration test harness.
*   **Trace Segment:**
    ```text
    ...
    [15] go_test (PASS)
    [16] go_build (PASS)
    [17] file_create "test_list_tools.json"  <-- Manual test setup
    [18] safe_shell "./hello < test_list_tools.json" <-- Manual verification
    [19] safe_shell "./hello < test_call_tool.json"
    [20] END
    ```
*   **Outcome:** Success (164s), but wasted ~40 seconds on redundant manual testing.

### Advanced Agent (Run 4060) - "The Professional"
*   **Context:** Sees professional tools (`code_review`, `go_diff`, `symbol_inspect`).
*   **Behavior:** It followed a standard engineering workflow: Implement -> Unit Test -> Build -> Submit. It assumed that if `go test` passes, the code is correct.
*   **Trace Segment:**
    ```text
    ...
    [8] go_test (PASS)
    [9] go_build (PASS)
    [10] END  <-- Immediate submission
    ```
*   **Outcome:** Success (136s). The system's automated validation layer confirmed the code worked perfectly.

## Conclusion

The presence of "Advanced" tools in the system prompt—even though they were never used—likely primed the model to adopt a **"Senior Engineer" persona**. 

*   **Standard Persona:** "I need to double-check everything manually to make sure I didn't break it."
*   **Advanced Persona:** "Tests passed. Build passed. Ready for review."

This "Context Priming" made the Advanced agent **better** (more efficient) by eliminating redundant verification steps, relying instead on the provided unit tests as the source of truth.

# GoDoctor v3.2 Roadmap: The "Agentic" Evolution

Based on the capability analysis and user feedback, this is the approved plan for v3.2.

## 1. New Tool: `scaffold` (The Generator)
Instead of modifying `write` to guess intent, we introduce a dedicated tool for scaffolding concepts.

*   **Purpose:** Quickly generate boilerplate so the LLM can "fill in the blanks" rather than writing from scratch.
*   **Mechanism:** Template-based generation (Go text/template).
*   **Templates:**
    *   `api_server`: `main.go` with HTTP server, `handler` package, router.
    *   `cli_app`: `cmd/root.go`, `flags`.
    *   `test_suite`: Table-driven test boilerplate for a given file.
    *   `readme`: Standard project structure.
*   **Benefit:** Reduces token usage (outputting 100 lines of boilerplate is expensive) and enforces best practices.

## 2. Enhancement: `edit` with Impact Analysis
We will solve the "Chicken and Egg" refactoring problem by providing **Information** rather than **Blocking**.

*   **Current Behavior:** Edits are checked for *local* validity (does this file compile?).
*   **New Behavior (Impact Analysis):**
    1.  Apply the edit.
    2.  Check local validity.
    3.  **Cross-Reference Check:** Use the Knowledge Graph to find all callers of the modified symbols.
    4.  **Impact Report:** Return a warning if those callers are now broken (e.g., "Edit successful, but broke 3 callers in `auth.go`").
*   **Benefit:** Enables the Agent to perform multi-file refactors sequentially ("I fixed the definition, now I see 3 errors, I will go fix them next").

## 3. Decisions on Existing Tools
*   **`open` / `describe`:** Status Quo maintained.
    *   `describe` depth will remain at 1 to prevent context flooding. LLMs should recursively explore if needed.
    *   `open` retains its name as the "Gateway" concept.

## 4. Implementation Priority
1.  **High:** `edit` Impact Analysis. (Core reliability feature).
2.  **Medium:** `scaffold` tool. (Productivity booster).

## 5. Next Steps
*   Update `internal/tools/edit` to implement Reverse Dependency checking.
*   Create `internal/tools/scaffold` package and define initial templates.

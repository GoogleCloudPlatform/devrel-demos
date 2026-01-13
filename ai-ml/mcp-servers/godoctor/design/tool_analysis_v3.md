# Tool Capability Analysis & Improvement Proposals (v3.1 - Revised)

## 1. Systemic Analysis: TOOLS AS A GRAPH

The previous analysis treated tools as isolated functions. This was incorrect. The tools form a **Stateful Workflow** where `open` is the "Gateway" that primes the Knowledge Graph for `describe` and `edit`.

### The "Session" Concept
*   **The State:** The Knowledge Graph (`internal/graph/manager`).
*   **The Primer:** `open(file)` -> Loads `file`'s package (and imports) into the Graph.
*   **The Consumers:**
    *   `describe(symbol)`: Only works efficiently if the symbol's package is already in the Graph.
    *   `edit(file)`: Relies on the Graph to verify that edits don't break existing references.

## 2. Capability Analysis (Revised)

### `open` (The Primer)
*   **Current Role:** "Load this context so I can work on it." + "Show me what I just loaded (Skeleton)."
*   **Critique:** The name `open` *is* accurate in the sense of "opening a workspace session context". However, the *output* is an Outline.
*   **Improvement:**
    *   **Side Effect:** Make explicit that `open` triggers a "Deep Scan" of dependencies.
    *   **Feature:** Add `related_files` to output. Since we loaded the graph, tell the user: "Opening `handler.go`. **Note:** This is tested by `handler_test.go` and called by `router.go`." This primes the agent to `open` those files too.

### `describe` (The Navigator)
*   **Current Role:** "explain X".
*   **Gap:** It assumes the user knows *what* to describe.
*   **Improvement (Interconnected):**
    *   If `open` returns a skeleton, `describe` should be the natural follow-up.
    *   **Feature:** `describe_package`. If I just `open("main.go")`, I might want `describe(package="main")` to see the architecture before diving into symbols.

### `edit` (The Verifier)
*   **Current Role:** "Change X".
*   **Gap:** It only validates *after* the edit.
*   **Improvement (Interconnected):**
    *   The `open` tool loaded the graph. `edit` should use that graph *before* applying changes to offer auto-complete or "smart-select" (e.g., "You selected lines 10-15, but that cuts a function in half. Selecting 10-20.").

## 3. Proposal: The "Focus" Workflow

We should reframe the toolset around the concept of **Focus**.
1.  **`focus(file)` (was `open`):**
    *   Signifies: "I am working on this file."
    *   Action: Priority-loads the package. Watcher prioritizes this path.
    *   Output: Skeleton + **Inbound Links** (Who calls code in this file?).

2.  **`explore(symbol)` (was `describe`):**
    *   Signifies: "I need details on this node in the graph."
    *   Action: Returns Source/Doc.

3.  **`verify()` (New Tool):**
    *   Signifies: "I made changes, is the graph consistent?"
    *   Action: Explicitly runs the type-checker on the "Focused" package and returns errors. *Decouples verification from editing.*

## 4. Final Verdict on Naming
*   You are right: `open` IS stateful (it hydrates the graph).
*   However, `open` is still overloaded (OS file handle vs Editor tab vs Context load).
*   **Strategy:** Keep the *concept* of "Opening a context" but potentially refine the name to `load_context` or `examine` to clarify that it's about *Knowledge Graph population* + *Visual Inspection*.

**Proposed Set:**
*   `examine(file)` -> Loads Graph, Returns Skeleton + Related Files.
*   `describe(symbol)` -> (Unchanged)
*   `edit(file)` -> (Unchanged)

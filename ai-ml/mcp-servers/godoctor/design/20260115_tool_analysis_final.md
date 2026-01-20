# Tool Capability Analysis: The "Smart" Workflow (v3.2)

## 1. Workflow Verification

Your described workflow matches the architecture I have implemented. Here is the confirmation:

| Step | User Intent | Architecture Reality | Matches? |
| :--- | :--- | :--- | :--- |
| **`open`** | **Gateway & Outline**: Hits the graph, returns skeleton only. | **YES**. `open` calls `Global.Load()`, hydrating the graph. It creates a skeletal `ast.File` (removing bodies) for the output. | ✅ Matches |
| **`describe`** | **Augmentation**: Shows implementation + **related type definitions**. | **YES**. `describe.go` calls `graph.FindRelatedSymbols`. It iterates the signature (params/results), finds the `types.Object`, and prints their source code alongside the main symbol. | ✅ Matches |
| **`edit`** | **Smart Replacement**: Replaces implementation using graph for checking. | **YES**. `edit` uses fuzzy matching to find the block, applies the change, runs `goimports` (formatting), and then **re-checks compilation** using the graph. | ✅ Matches |
| **`write`** | **Direct I/O**: Bypass match logic for creation/appending. | **YES**. `write` does simple file I/O operations but *still* verifies the result compiles. | ✅ Matches |

## 2. Capability Analysis: "Is it useful?"

The toolset is **highly capable** because it solves the "Context Window Problem":
*   Instead of dumping 500 lines of code to the LLM (`read_file`), you give it a 50-line map (`open`).
*   The LLM asks only for the 20 lines it needs (`describe`).
*   It gets the *hidden* context (the struct definition) automatically, preventing the "I need to see `User` struct" round-trip.

## 3. Improvement Proposals (Refining the "Smartness")

While the *structure* is correct, the *intelligence* can be deepened.

### Improvement 1: `describe` - The "Context Radius"
*   **Current:** Shows 1 level deep (types in signature).
*   **Problem:** If `GetUser` returns `User`, we see `User`. But if `User` has a field `RoleID` of type `Role`, we don't see `Role`.
*   **Proposal:** Add a `depth` parameter to `describe` (default 1) to allow fetching "Deep Context" for complex refactors.

### Improvement 2: `edit` - "Impact Warning"
*   **Current:** Checks if *file* compiles.
*   **Problem:** If I change `GetUser(id string)` to `GetUser(id int)`, the file might compile (if I fixed the body), but **callers** in other files will break. The current `edit` tool warns about compilation errors *in the edited package*, but we should explicitly check **Reverse Dependencies**.
*   **Proposal:** When `edit` finishes, run `FindReferences` on the modified symbol. If any reference is in a file that now fails to compile, **fail the edit** (or return a critical warning). Implementation: The graph already has `FindReferences`.

### Improvement 3: `write` - "Scaffold Intelligence"
*   **Current:** Dumb append.
*   **Problem:** "Create a test for this file" requires the LLM to know the package name, imports, etc.
*   **Proposal:** If `write` is creating a NEW file, automatically infer the `package` clause from the directory (using `go list` or graph) if the LLM omits it.

## 4. Conclusion
The names `open`, `describe`, `edit`, `write` **are appropriate** because they map to the *Human-AGI* mental model of interacting with an editor:
1.  **Open** the file list (Outline).
2.  **Describe** (Inspect) a specific thing.
3.  **Edit** it.

**Verdict:** No renaming needed. Focus on **Improvement 2 (Impact Warning)** as the next high-value feature.

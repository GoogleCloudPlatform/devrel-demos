# PDD Evaluation: Code-Aware GoDoctor (v1.5 - Final Recommendation)

## 1. Executive Summary of Changes
Based on the iterative feedback loop, the original proposal for a "Custom AST Indexer" has been rejected in favor of a **"Type-Aware Indexer"** leveraging `go/packages` and `go/types`. This decision prioritizes **correctness** and **stdlib reuse** over premature optimization, while maintaining the "Context-Aware" vision.

## 2. Core Strategic Decisions

### 2.1 Adoption of `go/packages` (The "Correct" Approach)
*   **Decision:** We will use `golang.org/x/tools/go/packages` to load semantic information.
*   **Rationale:**
    *   **Fact vs Guess:** It resolves types precisely (e.g., `u.Save` -> `User.Save`), eliminating hallucinations.
    *   **Simplicity:** It removes the need for complex custom scope-tracking logic.
    *   **Integration:** It handles build tags, modules, and dependencies natively.

### 2.2 Rejection of "Custom Symbol Structs"
*   **Decision:** The primary data models will be thin wrappers around `types.Object` and `packages.Package`.
*   **Rationale:** "Don't reinvent the wheel." The Go standard library models are robust and sufficient.

### 2.3 Real-Time Consistency via File Watching
*   **Decision:** Implement `fsnotify` to trigger incremental package reloads.
*   **Rationale:** "Business Critical." The agent must trust that its view of the code matches the disk state.

## 3. Revised Implementation Plan

### Phase 0: The "Correctness Spike" (Crucial First Step)
Before writing the server, we must validate the performance latency of the "Type-Aware" approach.
1.  **Script:** `spike/types_latency.go`.
2.  **Test:** Load `godoctor` logic itself. Measure time to `packages.Load`.
3.  **Validation:** If reload < 1s, proceed. If > 5s, we may need a hybrid approach (AST for fast edits, Types for deep reads).
    *   *Hypothesis:* Incremental reloading of a single package is sub-second.

### Phase 1: The Type-Aware Brain
1.  **State Manager:** A thread-safe cache (`sync.RWMutex`) mapping `importPath -> *packages.Package`.
2.  **Watcher:** `fsnotify` loop that invalidates and reloads varied packages.
3.  **API:** `GetSymbol(name, pkg) -> *types.Object` and `FindReferences(obj) -> []Location`.

### Phase 2: The Contextual Tools
1.  **`read_code`:** Returns file content + "Impact Report" (imports, definitions).
2.  **`describe`:** Uses `doc.New(pkg)` (on the loaded package) to format documentation and `types.Info.Uses` to find references.

### Phase 3: The Safe Editor
1.  **Pre-Check:** Ensure graph is consistent (no pending file events).
2.  **Post-Check:** Reload package after edit. If `packages.Load` returns Type Errors, rollback or report failure.

## 4. Final Recommendation
Proceed with updating the PDD to Version 2.0 reflecting this **Type-Aware Architecture**.

**Next Step:** Execute Phase 0 (The Spike).

# Product Design Document: Code-Aware GoDoctor (v3.0)

## 1. Executive Summary
**GoDoctor** will evolve into a **Type-Aware Development Assistant**. Abandoning previous heuristic approaches, it will leverage the official `go/packages` and `go/types` libraries to provide 100% accurate, compiler-verified context. To ensure responsiveness, it will employ a persistent caching strategy with real-time file watching.

## 2. Core Strategic Decisions

### 2.1 The "Type-Aware" Architecture
*   **Decision:** Use `golang.org/x/tools/go/packages` as the sole source of truth.
*   **Rationale:**
    *   **Correctness:** Eliminates hallucinations. `u.Save()` is resolved to `User.Save` by the compiler, not a guess.
    *   **Robustness:** Handles build tags, modules, and `cgo` natively.
    *   **Simplicity:** Reuses the Go standard library's robust data models (`types.Object`, `types.Type`).

### 2.2 Real-Time Consistency
*   **Decision:** Integrate `fsnotify`.
*   **Mechanism:**
    *   Server watches the module root.
    *   On file change -> Invalidate specific package in cache -> Background reload.
    *   *Goal:* The LLM always sees the disk state, not a stale memory state.

## 3. The Knowledge Graph (Architecture)

### 3.1 Data Model
We replace custom structs with standard Go types.

```go
type PackageState struct {
    Pkg *packages.Package
    // Metadata for cache invalidation
    LastLoaded time.Time
}

type StateManager struct {
    mu       sync.RWMutex
    // Map import path ("github.com/my/lib") to loaded package
    Packages map[string]*PackageState
}
```

### 3.2 Indexing Strategy
*   **Loading:** `packages.Load` with `NeedTypes | NeedSyntax | NeedTypesInfo`.
*   **References:** Use `types.Info.Uses` (map of `*ast.Ident` -> `types.Object`) to reverse-lookup usages.
*   **Documentation:** Use `go/doc` on the loaded `*packages.Package` to extract comments and examples.

## 4. Tool Evolution

### 4.1 `open` (The Entry Point)
**Replaces:** `read_code` (for Go files).
**Purpose:** Loads a file into the GoDoctor context and builds the Knowledge Graph for that unit of code.
*   **Args:** `file` (path to .go file).
*   **Logic:**
    1.  Parses the file and triggers a package load/index.
    2.  Analyzes upstream (dependencies) and downstream (usages) links.
*   **Returns:** A **Skeleton View** of the file:
    *   Package name.
    *   Imports.
    *   Global `const`/`var` blocks.
    *   Type definitions.
    *   Function/Method **signatures** (bodies hidden/collapsed).
    *   Comments.
    *   *Why?* Gives high-level structure without token bloat, forcing the LLM to use `describe` for details.

### 4.2 `describe` (The Explorer)
**Purpose:** Discover API surfaces and read implementation details.
*   **Args:** 
    *   `package` (optional, module path).
    *   `symbol` (optional, name of type/func).
    *   `file` (optional, local path).
    *   *Constraint:* At least `package` or `file` must be set.
*   **Logic:**
    *   **External (Std/Module):** Returns full documentation + examples (godoc style).
    *   **Internal (Local):** Returns **Full Implementation** (Source Code) + Docs + Examples (testable examples).
    *   **For Both:** Returns a **Usage Map** (Where is this declared? Who calls it?).
    *   **No Symbol?** Returns package overview or **Full File Content** (no skeleton, actual code).

### 4.3 `edit` (The Actor)
**Purpose:** Modify code with whitespace-agnostic matching and auto-fixing.
*   **Args:**
    *   `file`: Target file.
    *   `search_context`: Block to find.
    *   `replacement`: New code block.
    *   `autofix`: Similarity threshold (0-100, default 95). 0 = disabled.
*   **Logic:**
    1.  **Fuzzy Match:** Ignores whitespace/indentation. Uses Levenshtein for typos if within threshold.
    2.  **Apply:** Updates file content.
    3.  **Verify:** Checks for broken dependencies (upstream/downstream).
*   **Returns:**
    *   Success: "Modified file X."
    *   Failure: "Match not found. Suggestions: ..."
    *   Impact Warning: "Edit successful, but broke references in files A, B."

### 4.4 `write` (The Creator)
**Purpose:** Create new files or append to existing ones with verification.
**Modes:**
*   `append` (Default): Adds content to end of file (or creates if missing). Useful for adding new handlers/types without touching existing code.
*   `overwrite`: Replaces entire file content.
**Validation:**
*   Automatically identifies new imports in the written code.
*   Validates that used symbols match the imported API (using the Knowledge Graph).
*   *Warning:* "You used `auth.SignIn`, but package `auth` only exports `Login`."

## 5. Implementation Plan

### Phase 0: The Correctness Spike (CRITICAL)
**Goal:** Verify that `packages.Load` is fast enough for interactive use.
1.  Script: `spike/types_latency.go`.
2.  Metric: Time to reload a single package in a medium project.
3.  **Gate:** If reload > 2s, we must optimize (e.g., trimming scope).

### Phase 1: The Type-Aware Brain
1.  Implement `internal/state/manager.go`.
2.  Implement `fsnotify` watcher loop.
3.  Implement `open` tool logic (Skeletonizer).

### Phase 2: The Contextual Tools
1.  Implement `describe` with dual mode (Doc vs Source).
2.  Integrate `open` with State Manager.

### Phase 3: The Safe Editor
1.  Refactor `edit_code` to `edit`.
2.  Add "Impact Analysis" post-edit.

## 6. Tool API Specifications (v3.0)



**Note:** Internal contracts use `*types.Object`. External output is Markdown.



### 6.1 `open`

**Input:**

```json

{

  "file": "internal/user/model.go"

}

```

**Output (Skeleton):**

```go
package user



import (

    "github.com/google/uuid"

)



// User represents a registered account.
type User struct {

    ID   string

    Name string

}



// NewUser creates a user.

func NewUser(name string) *User
```



### 6.2 `describe`

**Input:**

```json

{

  "symbol": "User", 

  "package": "internal/user", 

  "file": "cmd/main.go" 

}

```

**Output:**

*   **Definition:** `type User struct { ID string; Name string }`

*   **Documentation:** "User represents a registered account."

*   **Usage:**

        *   `cmd/main.go:45`: `u := &user.User{}`

    

    ### 6.3 `edit`

    **Input:**

    ```json

    {

      "file": "internal/user/model.go",

    

  "search_context": "func NewUser(name string) *User { ... }",

  "replacement": "func NewUser(name string, email string) *User { ... }",

  "autofix": 95

}
```

**Output:**

*   **Status:** Success

*   **Impact Warning:** "Breaking change: Function signature changed. Call site in `main.go:45` needs update."





### 6.4 `write`

**Input:**

```json

{

  "name": "internal/user/new_file.go",

  "content": "package user\n\nfunc Helper() {}",

  "mode": "overwrite"

}

```

**Output:**

*   **Status:** Success

*   **Validation:** "Warning: Imported `fmt` but did not use it."

```
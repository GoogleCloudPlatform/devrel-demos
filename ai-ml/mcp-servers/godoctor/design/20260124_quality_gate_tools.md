# Design Proposal: Unified Quality Gates & Intelligent Hints

**Date:** 2026-01-24
**Status:** Draft

## 1. Problem Statement

Analysis of agent behavior (Experiment 91) reveals significant friction in the standard Go development workflow:
1.  **Fragmented Verification:** Agents rarely use `verify_build` or `verify_tests`, preferring `run_shell_command` with `go test` (which fails 15-25% of the time).
2.  **Lack of Guardrails:** Agents often fix syntax errors but neglect to run tests or linters, leading to regressions.
3.  **Shell Dependency:** High volume of shell calls for basic tasks like `go mod tidy` and project scaffolding (`mkdir`, `go mod init`).
4.  **Generic Errors:** Failure messages from compilers or linters are passed raw to the agent, often leading to hallucinated fixes (e.g., guessing package paths).

## 2. Strategic Vision: The "Smart Build" Pipeline

Agents view "building" as a mandatory step, whereas "verifying" is often treated as optional. To ensure quality guardrails are respected, we will position our quality gate *as the build tool itself*.

### 2.1. New Tool: `smart_build` (Replaces `verify_build` & `verify_tests`)

This tool is positioned as the **primary way to compile Go code**. It wraps the standard `go build` command but enforces a "batteries included" workflow that includes formatting, dependency cleanup, testing, and linting.


**Signature:**
```go
type SmartBuildArgs struct {
    Dir         string `json:"dir"`          // Project root (default: current)
    Packages    string `json:"packages"`     // Packages to build (default: ./...)
    RunTests    bool   `json:"run_tests"`    // Default: true. Run unit tests after build.
    RunLint     bool   `json:"run_lint"`     // Default: true. Run linter after tests.
    AutoFix     bool   `json:"auto_fix"`     // Default: true. Run go mod tidy / go fmt before build.
}
```

**Workflow:**
1.  **Preparation (Auto-Fix):**
    *   Execute `go mod tidy` to resolve missing `go.sum` entries.
    *   Execute `gofmt -w` to ensure syntax compliance.
2.  **Compilation (The Hook):**
    *   Run `go build [packages]`.
    *   *Failure:* Analyze compiler output. If specific errors (like "undefined") are found, generate **Hints** and return failure.
3.  **Validation (The Value Add):**
    *   If build succeeds and `RunTests` is true: Execute `go test [packages]`.
    *   If tests pass and `RunLint` is true: Execute `golangci-lint` (or `go vet`).
4.  **Reporting:**
    *   Return a consolidated report. If the build works but tests fail, the tool returns a **FAILURE**. This forces the agent to fix the tests before considering the "build" task complete.

**Output:**
```markdown
## Smart Build: FAILED

### 🛠️ Build: SUCCESS
The code compiles successfully.

### 🧪 Tests: FAILED
- `pkg/api/handler_test.go`: `TestCreateUser` failed.
  > Expected 201, got 500

**Hint:** The test failed with a 500 error. This often indicates a nil pointer dereference or an unhandled error in the handler. Check the server logs.
```


### 2.2. New Tool: `project_init`

To reduce the `mkdir` -> `go mod init` -> `go get` shell loop.

**Signature:**
```go
type ProjectInitArgs struct {
    Path         string   `json:"path"`          // Target directory
    ModulePath   string   `json:"module_path"`   // e.g., github.com/user/my-app
    Dependencies []string `json:"dependencies"`  // e.g., ["github.com/go-chi/chi/v5"]
}
```

**Behavior:**
1.  Recursively creates `Path`.
2.  Runs `go mod init`.
3.  Runs `go get` for each dependency.
4.  Creates a skeleton `main.go` (Hello World) to ensure the module is valid.

## 3. Intelligent Hint System (Global)

We will implement a `HintProvider` system that analyzes `stdout`/`stderr` from all GoDoctor tools (`smart_edit`, `verify_quality`, etc.) and appends actionable advice to the tool output.

### 3.1. Heuristic Library

| Detected Pattern | Heuristic / Trigger | Generated Hint |
|---|---|---|
| **Missing Import** | `undefined: [PackageName]` | "Package '[PackageName]' is undefined. Did you forget to import it? Use `smart_edit` to add the import." |
| **Missing Mod Entry** | `missing go.sum entry` | "Dependencies are out of sync. `verify_quality` attempted `go mod tidy`, but it failed. Check if the package name is correct." |
| **Unused Variable** | `declared but not used` | "Go requires all variables to be used. Remove the variable or use `_` to ignore it." |
| **Test Timeout** | `panic: test timed out` | "The test hung. Look for infinite loops or unclosed channels/connections." |
| **Hallucinated Package** | `module ... does not contain package` | "The package path appears incorrect. Use `read_docs` or `run_shell_command 'go list ...'` to find the correct import path." |

### 3.2. Integration with `smart_edit`

`smart_edit` currently fails silently or with generic errors if the match is poor.

*   **Improvement:** If `smart_edit` fails to match the `old_string` exactly but finds a candidate with >80% similarity:
    *   *Action:* Reject the edit (safety first).
    *   *Hint:* "I found a block that looks 85% similar. Here is the actual code in the file: `[Snippet]`. Please retry with this exact string."

## 4. Implementation Plan

### Phase 1: The Quality Gate
1.  Create `internal/go/quality` package.
2.  Implement `smart_build` tool aggregating build, test, and lint.
3.  Deprecate `verify_build` and `verify_tests` (hidden from tool listing but kept for back-compat, or removed if we are brave).

### Phase 2: The Hint Engine
1.  Create `internal/hints` package.
2.  Implement regex-based matchers for common Go errors.
3.  Hook `hints.Analyze(output)` into `run_shell_command` (if we hook it) and all internal tool outputs.

### Phase 3: Project Scaffolding
1.  Implement `project_init`.

## 5. Success Metrics
*   **Adoption Rate:** >80% of verification steps use `smart_build` instead of `go test` shell commands.
*   **Shell Usage:** Reduction of `run_shell_command` usage by 30% (specifically `go mod`, `mkdir`, `go test`).
*   **Success Rate:** Increase in overall task success rate due to automated `go mod tidy` and lint checks catching issues early.

## 6. Evolution of `smart_edit`

Observations of agent failures indicate that `smart_edit` needs to be more communicative when it fails, and more powerful for complex refactors.

### 6.1. Enhanced Failure Hints

When `smart_edit` rejects an edit, it must explain *why* and *how to fix it*.

1.  **Fuzzy Match Rejection:**
    *   *Condition:* `best_match_score` is between 0.8 and 0.95 (threshold).
    *   *Hint:* "I found a block that looks similar but differs. Here is the actual code in the file: `[Snippet]`. Please retry with this EXACT text as `old_string`."
    *   *Value:* Prevents the "hallucinated whitespace" loop.

2.  **Ambiguity Resolution:**
    *   *Condition:* Multiple identical matches found.
    *   *Hint:* "I found 3 occurrences of this string. To edit the one you want, please retry with `start_line=[N]` and `end_line=[M]`. The matches are at lines: 10, 45, 90."

3.  **Large File Warning:**
    *   *Condition:* File > 500 lines and search is slow or ambiguous.
    *   *Hint:* "This file is large. Using line numbers (`start_line`, `end_line`) is strongly recommended to ensure precision."

### 6.2. Improving Append Mode visibility

While `smart_edit` currently supports "Append Mode" (by leaving `old_content` empty), this "magic value" pattern is often missed or misused.

**Proposal:**
*   **Explicit Flag:** Add an `append` boolean to the tool arguments.
*   **Hinting:** If the agent attempts to match the very end of a file (e.g., matching the last `}` to add code after it), the tool should suggest: *"It looks like you are trying to append code. Use `append=true` (and leave `old_content` empty) for a safer, conflict-free append."*

### 6.3. Future Capability: `smart_patch` (Multi-File Edit)

Atomic refactoring often requires changing multiple files simultaneously (e.g., changing a function signature and its call sites). Doing this sequentially breaks the build in between steps, confusing the agent.


**Concept:** A new tool (or mode) that accepts a list of edits.

**Signature:**
```go
type SmartPatchArgs struct {
    Edits []struct {
        FilePath  string `json:"file_path"`
        OldString string `json:"old_string"`
        NewString string `json:"new_string"`
    } `json:"edits"`
    DryRun bool `json:"dry_run"` // Default: false
}
```

**Workflow:**
1.  **Verify All:** Check that *all* `OldString`s match their respective files.
2.  **Atomic Apply:** If verification passes, apply all edits in memory.
3.  **Write:** Write all modified files to disk.
4.  **Report:** "Successfully applied 5 edits across 3 files."



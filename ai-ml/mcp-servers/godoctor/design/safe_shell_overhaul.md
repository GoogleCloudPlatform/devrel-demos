# Specification: Safe Shell Overhaul (Advisory & Integrity)

## Goal
Transform `safe_shell` from a "blocked/unblocked" gatekeeper into an **opinionated, helpful assistant**. Instead of just denying commands, it should guide agents toward better tools while strictly protecting the integrity of the codebase.

## Core Philosophy
1.  **No "Force" Mode:** Safety is non-negotiable. Redundant commands are hard-blocked to force tool adoption.
2.  **Advisory First:** If an agent uses a generic shell tool (`ls`, `cat`) when a specialized one exists (`file_list`, `file_read`), allow it but prepend an **Advice** message.
3.  **Code Integrity Barrier:** Shell tools (`rm`, `mv`, `sed`) are **strictly forbidden** from modifying Go source files (`*.go`) to prevent corruption. Agents must use `file_edit` or `file_create`.

## API Changes
*   **Remove:** `Force` parameter from `Params` struct.
*   **Update:** `validateCommand` signature.

## Validation Logic

The single `DenyList` will be split into three distinct categories:

### 1. Hard Block List (Returns Error)
*   **Danger:** `sudo`, `chown`, `chmod`, `ssh`, `wget`, `curl` (with file flags).
*   **Process Safety:** `vim`, `nano`, `top` (Interactive).
*   **Complexity:** `git` (User domain).
*   **Go Redundancy:** `go build`, `go test`, `go mod`, `go get`, `go install`, `go doc`, `go vet`. (These have complex, specialized tools that *must* be used).
*   **System Integrity:** `rm -rf /` (Root path protection).

### 2. Advisory List (Returns Hint + Output)
*   **Discovery:** `ls` → Hint: *"Use `file_list` for a standard recursive view."*
*   **Reading:** `cat`, `head`, `tail` → Hint: *"Use `file_read` for line numbers and analysis."*
*   **Search:** `grep`, `find` → Hint: *"Use `file_search` (text) or `symbol_inspect` (code)."*

### 3. Dynamic Integrity Barrier (The "Code Guard")
*   **Triggers:** `rm`, `mv`, `cp`, `sed`, `awk`, `echo` (with redirection).
*   **Check:** Does any argument end in `.go`?
*   **Action:** **BLOCK**.
*   **Message:** *"Modifying .go files via shell is forbidden to ensure integrity (goimports, syntax check). Use `file_edit`."*

## Output Formatting
If a command triggers an Advisory rule, the output will be wrapped:

```text
[ADVICE]: Use 'file_list' for a structured view of the directory.
---
bin/
cmd/
...
```

## Implementation Plan
1.  **Refactor `run.go`:** Remove `Force` from `Params`.
2.  **Implement Logic:** Rewrite `validateCommand` to return `(advice string, err error)`.
3.  **Update Tests:** Verify "Hard Block" (error), "Advisory" (success + hint), and "Code Guard" (error on .go).

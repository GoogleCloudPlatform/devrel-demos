# Specification: Line Number Support for File Tools

## Goal
Enable targeted reading and manipulation of files by specifying line number ranges (`start_line` and `end_line`). This capability reduces token usage and improves focus for LLM agents.

## Affected Tools
1.  `file_edit` (Implemented)
2.  `file_read` (Proposed)

## Design

### 1. Shared Logic
The line offset calculation logic (`getLineOffsets`) should be centralized to ensure consistency across tools.

*   **Location:** `internal/tools/shared/lines.go`
*   **Function Signature:** `func GetLineOffsets(content string, startLine, endLine int) (int, int, error)`

### 2. `file_read` Update

**Objective:** Allow reading a specific range of lines.

**Parameters:**
Update `Params` struct in `internal/tools/file/read/read.go`:
```go
type Params struct {
    Filename  string `json:"filename"`
    StartLine int    `json:"start_line,omitempty"`
    EndLine   int    `json:"end_line,omitempty"`
}
```

**Behavior:**
1.  **Validation:** Check if `start_line` and `end_line` are valid.
2.  **Reading:**
    *   Read the full file content (disk I/O is cheap compared to tokens).
    *   Calculate offsets using `GetLineOffsets`.
    *   Extract the substring.
3.  **Analysis (AST/Symbols):**
    *   **Partial Read:** If line numbers are specified, **skip AST analysis and symbol extraction**. Parsing a partial Go file (e.g., a function body without package declaration) will likely fail or produce noisy errors.
    *   **Return:** Return only the text content of the requested lines, wrapped in markdown.
    *   **Full Read:** If no lines are specified, retain existing behavior (full parse + symbols).

**Output Format (Partial):**
```markdown
# File: path/to/file.go (Lines 10-20)

```go
func MyFunc() {
    ...
}
```
*Note: Partial read - analysis skipped.*
```

## Implementation Plan
1.  **Refactor:** Move `getLineOffsets` from `internal/tools/file/edit/edit.go` to `internal/tools/shared` as `GetLineOffsets`.
2.  **Update `file_edit`:** Update imports to use the shared function.
3.  **Update `file_read`:** Implement the `Params` change and logic branching (Full vs Partial).

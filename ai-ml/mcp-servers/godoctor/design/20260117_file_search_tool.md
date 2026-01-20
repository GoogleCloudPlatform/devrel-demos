# Specification: Generic File Search Tool (`file_search`)

## Status: Shelved (2026-01-17)
This tool was shelved following the implementation of `safe_shell` V2. Since `safe_shell` now uses an Advisory system, generic tools like `grep` are no longer hard-blocked; they return the requested data alongside a suggestion to use more specialized tools. Consequently, a custom `file_search` would be redundant with standard `grep` and would drift away from the project's focus on specialized Go-aware tools. Agents should use `safe_shell` with `grep` for non-Go content search.

## Goal
Provide a way for agents to search for text patterns across all files in a project, not just Go files. This bridges the gap between `file_list` (locating files) and `file_read` (examining content).

## Tool Definition

*   **Internal Name:** `file.search`
*   **External Name:** `file_search`
*   **Title:** Search Project Content
*   **Description:** Perform a recursive text search throughout the project directory. Use this to find strings in READMEs, Dockerfiles, configurations, or other non-Go source files.

## Parameters
```go
type Params struct {
    Query      string `json:"query" jsonschema:"The text string to search for"`
    Path       string `json:"path,omitempty" jsonschema:"The directory to search in (default: project root)"`
    IgnoreCase bool   `json:"ignore_case,omitempty" jsonschema:"Whether to perform a case-insensitive search (default: true)"`
    Include    string `json:"include,omitempty" jsonschema:"Optional glob pattern to restrict files (e.g. '*.md')"`
}
```

## Behavior
1.  **Scope:** Recursively walk the directory tree starting from `Path`.
2.  **Exclusions:** Automatically skip the `.git` directory and any files/folders ignored by `.gitignore` (if feasible).
3.  **Search Logic:** Use a simple substring match for performance and predictability.
4.  **Limits:**
    *   **Max Matches:** Stop searching after 50 matches to prevent overwhelming the agent.
    *   **Binary Files:** Skip files that appear to be binary.
5.  **Output Format:**
    Return a list of matches including the file path, line number, and a snippet of the matching line.

    ```markdown
    Found 3 matches for "TODO":

    - `README.md:12`: // TODO: Add setup instructions
    - `internal/config/config.go:45`: // TODO(refactor): Move this to a separate package
    - `design/roadmap.md:5`: - [ ] TODO: Implement file_search tool
    ```

## Implementation Plan
1.  Add `file.search` to `internal/toolnames/registry.go`.
2.  Create package `internal/tools/file/search`.
3.  Implement the recursive search using `filepath.Walk`.
4.  Register the tool in `internal/server/server.go`.

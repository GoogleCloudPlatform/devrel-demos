# Friction Log: Session 2026-01-23

**Summary:**
This session focused on testing and refining the `godoctor` toolset. While the tools are generally powerful, we encountered significant friction with the `file_edit` tool's fuzzy matching logic and API design ambiguities in `file_list`.

## 1. `file_edit` Stability & Context Matching
**Severity:** High
**Context:** Attempting to refactor `internal/tools/file/outline/outline.go` to filter standard library imports.

### The Issue
I attempted to replace a `for` loop block using `file_edit` with `search_context`. This failed **3 times consecutive times** with the error:
> `edit produced invalid Go code: ... expected ';', found 'if' ...`

The tool attempts to fuzzy-match the context, apply the patch, and *then* run `gofmt`/syntax check. The failures suggest that the fuzzy matcher often misaligned the replacement, resulting in unmatched braces or broken syntax scopes. The error message was helpful in identifying *that* it failed, but not *how* the patch was misapplied.

### The Workaround
The user eventually instructed me to use `start_line` and `end_line` to delimit the replacement.
*   **Result:** The edit succeeded immediately on the first try.

### Recommendation
*   **Agent Behavior:** When `file_edit` fails on syntax, the agent should immediately fallback to reading the file with line numbers and retrying with explicit line ranges, rather than retrying the fuzzy match with slightly different context.
*   **Tool Improvement:** The tool could perhaps offer a "dry run" or return the "bad code" (with a diff) in the error message so the agent can see *how* the fuzzy match failed (e.g., "I replaced lines 70-75, but that left a dangling brace on line 76").

## 2. `file_list` Parameter Ambiguity
**Severity:** Medium
**Context:** User requested `file_list(path="internal", depth=3)`.

### The Issue
The output returned only **Depth 1**.
Investigation revealed a conflict between two parameters:
*   `Recursive` (bool)
*   `Depth` (int)

The logic in `list.go` effectively said "If Recursive is implicitly false (or not handled), set Depth to 1", overriding the user's explicit `Depth=3`. This is a classic "Split Source of Truth" API problem.

### The Fix
We refactored the tool to remove the `Recursive` parameter entirely. Now, `Depth` is the single source of truth:
*   `Depth=0` -> Default to 5 (Deep tree)
*   `Depth=1` -> Flat list (old "non-recursive")
*   `Depth=N` -> N levels deep

### Recommendation
*   **API Design:** Avoid boolean flags that duplicate the functionality of integer/enum counters.

## 3. `file_outline` Information Overload
**Severity:** Low (UX)
**Context:** User felt the outline tool returned "too much info".

### The Issue
The `file_outline` tool included `fmt`, `os`, and `context` imports in its "Appendix: External Imports". For a standard Go file, this creates significant token noise with low value (we know what `fmt` does).

### The Fix
We implemented a heuristic to filter out imports that don't look like domains (no `.` in the first path segment).

### Recommendation
*   **Default Behavior:** Tools targeting LLMs should default to "Aggressive Filtering". It is better to hide standard library docs and force the agent to ask for them (via `go_docs`) than to burn tokens on every file read.

## 4. `file_read` & Discovery (Positive)
**Severity:** None (Success)
**Context:** updating documentation across multiple packages.

The workflow of:
1.  `file_list` (to find structure)
2.  `read_file` (to identify targets)
3.  `file_edit` (to update comments)
...worked seamlessly. The `file_list` tool is significantly faster and cleaner for this than `ls -R`.

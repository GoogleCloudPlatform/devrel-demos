# Proposal: Smart `edit_code` Tool for MCP

## Executive Summary

This proposal outlines the design for a new, robust file editing tool, `edit_code`, to replace the existing brittle `replace` and `write_file` primitives in the Model Context Protocol (MCP) server.

The current editing workflow is prone to high failure rates due to:
1.  **Context Mismatch:** `replace` fails if the LLM's memory of the file differs even slightly (whitespace, indentation) from the disk state.
2.  **Abandonment:** Repeated failures cause agents to revert to `write_file` (full overwrite), which is token-expensive and prone to introducing syntax errors or reverting previous fixes.
3.  **Ambiguity:** Lack of safeguards against replacing the wrong code block when patterns repeat.

**The `edit_code` tool solves this by introducing:**
*   **Fuzzy Matching:** Using Levenshtein/Diff-based scoring to find targets even with minor discrepancies.
*   **Unified Interface:** Combining "replace block" and "overwrite file" capabilities.
*   **Safety Guardrails:** Enforcing uniqueness for matches and validating syntax after edits.

This tool aims to reduce agent frustration, minimize token usage, and increase the success rate of autonomous coding tasks.

---


## 2. General Description

The `edit_code` tool acts as a smart patch utility. It takes a search block (context), locates it within the target file using a scoring algorithm, and replaces it with new content.

### Key Features

1.  **Fuzzy Search:** It doesn't require an exact byte-for-byte match. It calculates a "Match Score" (0-100%).
    *   If **100% (Exact):** Apply immediately.
    *   If **> Threshold (e.g., 90%)** AND **Unique:** Apply the change (assuming minor whitespace/comment drift).
    *   If **Ambiguous (Multiple Matches):** Fail and report locations to force disambiguation.
    *   If **Low Score:** Fail and report the "Best Match" diff to help the agent self-correct.

2.  **Mode Switching:**
    *   `replace_block`: The default, safe mode for surgical edits.
    *   `replace_all`: For refactoring repeated patterns across a file.
    *   `overwrite_file`: The "nuclear option" for creating new files or total rewrites, explicitly requested.

3.  **Verification Loop (Optional but recommended):**
    *   The tool can accept a `validate_command` (e.g., `go vet`) to run on the temporary state. If validation fails, the edit is aborted, and the linter error is returned.

---


## 3. Algorithm & Logic

### Input Parameters
*   `file_path` (string): Target file.
*   `search_context` (string): The code block to find (not required for `overwrite_file`).
*   `new_content` (string): The replacement code.
*   `strategy` (enum): "single_match" (default), "replace_all", "overwrite_file".
*   `threshold` (float): Similarity tolerance (default 0.9).

### Execution Flow

1.  **Read File:** Load target file content.
2.  **Match Finding:**
    *   If `overwrite_file`: Skip matching.
    *   If `replace_*`: Scan file for `search_context`.
        *   Compute similarity score (Levenshtein or Diff-ratio) for sliding windows or structural blocks.
        *   Collect all candidates with `score > threshold`.
3.  **Ambiguity Check:**
    *   If `candidates == 0`: **FAIL**. Return "No match found. Best candidate at line X (Score Y%). Diff: ..."
    *   If `candidates > 1` AND `strategy == "single_match"`: **FAIL**. Return "Ambiguous match. Found N occurrences at lines A, B, C. Please add more context."
4.  **Application (In-Memory):**
    *   Apply replacement(s) to the **in-memory buffer**. The actual file on disk remains completely untouched at this stage.
5.  **Validation (Pre-commit):**
    *   **Syntax Check (Strict):**
        *   Mechanism: Parse the **buffer content** using `go/parser.ParseFile`.
        *   **Gate:** If this returns errors (e.g., unmatched braces, bad keywords), the edit is **ABORTED**. The disk file is **NEVER** modified, preventing corruption.
        *   **Feedback:** The tool returns the *exact* parser error (e.g., `expected '}', found 'EOF' at line 120`) to the agent, enabling immediate self-correction in the next turn.
        *   *Note:* This does not check for unused variables or type errors, only structural validity.
    *   **Auto-Correction (Best Effort):**
        *   Mechanism: Run `goimports` on the buffer.
        *   **Goal:** Automatically fix missing imports or formatting issues that would otherwise cause a build failure.
        *   **Auto-Fix Scenarios:**
            *   **Missing Imports:** If the code uses `fmt.Println` but lacks `import "fmt"`, `goimports` is run to insert it.
            *   **Unused Imports:** If an edit removes the last usage of a package, `goimports` removes the import line.
            *   **Context Typos (Distance ≤ 1):** If the `search_context` has a single-character typo compared to the actual file content, the tool treats it as a high-confidence match and applies the edit automatically.
    *   **Build/Test Check (Soft):**
        *   **Action:** Write the buffer to a **temporary file** (e.g., in `/tmp` or adjacent hidden file) to run `go build` or `go test`.
        *   If Pass: Proceed to Commit.
        *   If Fail: **Proceed to Commit** (to allow multi-step refactors) but return the error as a "Warning".
        *   *Output:* "Success: Edit applied. **Warning:** Build failed (`undefined: NewField`). You may need to update dependent files."
6.  **Commit (Write to Disk):**
    *   **Action:** Only if the Strict Syntax Check passed, overwrite `file_path` with the validated buffer content.
    *   **Guarantee:** This ensures the file is always in a parseable state, even if it has compiler errors.

---

## 4. Discussion & Trade-offs

### Handling Multi-File Refactoring
Validation is tricky when changes span multiple files. If `FileA` changes signatures, `FileB` is broken until updated.
*   **Problem:** If `edit_code` enforces "Build Passes", the agent is deadlocked (can't fix A because B breaks, can't fix B because A breaks).
*   **Solution:** **Soft Validation**. The tool applies the edit if it is *syntactically* valid, even if it causes *semantic* (compiler) errors. The error report guides the agent's next step ("Now fix FileB").

### "Replace First" vs. "Replace All" vs. "Unique"
We explicitly **reject** "Replace First" as a default behavior. It is non-deterministic in large files where an agent might blindly match a common pattern (e.g., `if err != nil`) intending to fix the 10th occurrence but breaking the 1st.
*   **Decision:** Default to `single_match` (Unique). This forces the agent to provide enough context (surrounding lines) to disambiguate the target, ensuring safety.

### The "Abandonment" Problem
Agents hate friction. If a tool fails twice, they stop using it.
*   **Solution:** The "Best Match" error message is crucial. Instead of a hard "No", it says "Almost". This acts as a hint ("You missed a comma"), turning a failure into a correction step, keeping the agent in the loop.

### Efficiency
*   **Levenshtein:** Fast enough for typical source files (< 10k lines).
*   **Diff-based:** Even faster (`git diff` algorithms).
*   **Token Savings:** Prevents the need to read/write the entire file for small changes, saving massive amounts of context window space and generation costs.

---


## 5. Sample Interaction

### Scenario 1: Successful Fuzzy Match (Typo in Agent Memory)
**User Goal:** Rename function `OldFunc` to `NewFunc`.
**Agent Input:**
```json
{
  "file_path": "main.go",
  "search_context": "func OldFunc() {\n  fmt.Println(\"Old\")\n}",
  "new_content": "func NewFunc() {\n  fmt.Println(\"New\")\n}"
}
```
**File State (Disk):**
```go
// Comment added by other dev
func OldFunc() {
  fmt.Println("Old")
}
```
**Result:**
*   Exact Match: 0% (Due to comment/whitespace).
*   Fuzzy Match: 98% found at line 20.
*   **Action:** Tool applies change.
*   **Output:** `Success: Replaced block at line 20 (Match Score: 98%).`

### Scenario 2: Ambiguity Failure
**Agent Input:**
```json
{
  "search_context": "return err",
  "new_content": "return fmt.Errorf(\"failed: %w\", err)"
}
```
**Result:**
*   **Output:** `Error: Ambiguous match. Found 12 occurrences of "return err". Please provide more surrounding code (e.g., the function signature) to identify the specific target.`

### Scenario 3: Near Miss (Self-Correction Hint)
**Agent Input:** (Agent forgets the argument type)
```json
{
  "search_context": "func Process(data string)",
  "new_content": "..."
}
```
**File State:** `func Process(data []byte)`
**Result:**
*   **Output:** `Error: No match found. Best candidate at line 50 (Score: 85%).
    Diff:
    - func Process(data string)
    + func Process(data []byte)
    
    Please correct your search_context.`

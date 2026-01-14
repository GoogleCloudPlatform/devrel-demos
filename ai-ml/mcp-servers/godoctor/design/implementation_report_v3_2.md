# Implementation Report: GoDoctor v3.2 (Impact Analysis)

## 1. Executive Summary
The `edit` tool has been successfully enhanced with **Impact Analysis**. It now provides safety guarantees not just for the file being edited, but for the entire package ecosystem in the workspace.

## 2. Technical Implementation
### Knowledge Graph (`internal/graph`)
*   **Added `FindImporters(pkgPath)`**: Allows efficient lookup of reverse dependencies.
*   **Enhanced `Invalidate(dir)`**: Enables synchronous re-validation of dependent packages.

### Edit Tool (`internal/tools/edit`)
*   **Logic Flow**:
    1.  Apply edit to target file.
    2.  Check for local compilation errors.
    3.  **Cross-Reference Check**: If local check passes, iterate over all importers.
    4.  **Synchronous Re-validation**: Invalidate and Load each importer to check for broken API usage.
    5.  **Reporting**: Append "IMPACT WARNING" to the tool output if breakages are detected.

## 3. Verification
*   **Test Case**: `internal/tools/edit/impact_test.go`
*   **Scenario Verified**:
    *   `pkg/a` defines `Hello()`.
    *   `pkg/b` calls `a.Hello()`.
    *   `edit` changes `Hello()` to `Hello(name string)`.
    *   **Result**: Tool reports success for `pkg/a` edit but explicitly warns that `pkg/b` is now broken.
*   **Status**: ✅ Passed.

## 4. Deliverables
*   `internal/tools/edit/edit.go` (Updated)
*   `internal/graph/manager.go` (Updated)
*   `internal/tools/edit/impact_test.go` (New)

The system is now ready for use.

# Intent-Driven Tooling Architecture (v1.0 Vision)

**Date:** 2026-01-23
**Status:** Finalized

## 1. Philosophy: Intent over Implementation

Current tool names (`file_read`, `go_build`) describe the **implementation** (what the tool does).
The new naming convention describes the **intent** (what the agent wants to achieve).

This shift reduces the cognitive load on the LLM. Instead of translating "I need to check if this code works" to "I should run `go_build`", the agent maps directly to "I should `verify_build`".

## 2. The "Lite" Strategy (Stability & Memory Safety)

To solve the critical 18GB memory leak and ensure system stability, the custom Knowledge Graph (`internal/graph`) has been **removed**. The toolset has transitioned to a "Lite" model that relies on on-demand file parsing rather than global indexing.

**Consequences:**
*   **Zero Leak Risk:** No background indexing or recursive dependency loading.
*   **Loss of Impact Analysis:** `smart_edit` no longer checks reverse dependencies.
*   **Loss of Global Search:** `explain_symbol` and `symbol_rename` are removed until a full `gopls` integration wave.

## 3. Final Toolset (v1.0 - Lean Edition)

This inventory prioritizes "Go-Native" workflow over generic shell emulation. It uses active, intent-based naming to guide the agent toward the most effective tool for each task.

### Core Workflow
| Tool | Intent | Key Params | Description |
| :--- | :--- | :--- | :--- |
| **`list_files`** | Map the territory. | `path`, `depth` | Survey the directory structure. Replaces noisy shell `ls`. |
| **`smart_read`** | Inspect code. | `filename`, `outline` (bool), `lines` | The universal reader. Use `outline=true` to see structure, or line ranges for snippets. |
| **`smart_edit`** | Apply changes safely. | `filename`, `old_content`, `new_content` | Precision editing with Levenshtein matching and auto-formatting (gofmt). |
| **`file_create`** | Scaffold new files. | `filename`, `content` | Initialize new source files or configuration. |

### Quality & Verification
| Tool | Intent | Key Params | Description |
| :--- | :--- | :--- | :--- |
| **`verify_build`** | Verify compilation. | `packages` | Compile the project to catch syntax and type errors. Superior to shell because it parses failures and provides fix hints. |
| **`verify_tests`** | Verify logic. | `packages`, `coverage` (bool) | Run tests with automated reporting. Provides structured Pass/Fail counts and "Natural" total coverage (percentage of untested code). |
| **`add_dependency`** | Manage modules. | `packages` | **Superior to `go get`**: Installs modules and *immediately* returns their full documentation and API signatures to prevent hallucination. |
| **`code_review`** | Expert feedback. | `file_content` | Submits code for an expert-level Go review focused on concurrency, idioms, and maintainability. |

### Maintenance (Specialized)
| Tool | Intent | Key Params | Description |
| :--- | :--- | :--- | :--- |
| **`check_api`** | Assess API risk. | `old`, `new` | Detect breaking changes between versions (requires `apidiff`). |
| **`modernize_code`** | Proactive cleanup. | `dir`, `fix` (bool) | Automatically upgrade legacy Go patterns to modern standards. |

## 4. Deep Dive: `smart_read` Consolidation

**Logic:**
If `outline=true`, the tool uses `go/parser` to strip function bodies and return a structural map. Otherwise, it returns full content or a line-numbered snippet. This provides a single entry point for all inspection needs.

## 5. Next Wave: `gopls` Integration
Advanced features like "Find References", "Jump to Definition", and "Semantic Rename" are postponed and will be reintroduced via a managed `gopls` session in a future update.
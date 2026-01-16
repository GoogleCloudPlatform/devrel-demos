# godoctor Refactor Specification Report (v7)

## 1. Mission & Vision

**Mission:** To provide AI agents with a "Senior Partner" capability for Go development—reducing model hallucination, dramatically improving efficiency (token usage and inference speed), and supporting a natural, fluid development flow.

**Vision:** `godoctor` enables a **Context-Aware Development Environment**. Unlike standard file editing tools which operate in the "Text World" (prone to syntax errors and whitespace hallucinations), `godoctor` operates in the **"Semantic World"** of the Go compiler. It allows validation of ideas before text is even written, ensuring that every code change is syntactically valid and idiomatic.

## 2. Core Use Cases

`godoctor` supports high-level software engineering tasks:

1.  **Application Development:** Create apps with minimal resources; verify imports/types in real-time.
2.  **Refactoring:** Safely rename symbols, extract functions, and update interfaces across files without breaking dependencies.
3.  **Modernization:** Upgrade dependencies checking for API breakages, and leverage new compiler features (e.g., `min/max`, `slices`).
4.  **Feature Addition:** Add features with strict adherence to quality gates (linting, tests).
5.  **Reverse Engineering:** Reason about complex logic using semantic navigation (not just text search).

## 3. Tool Naming & Methodology

| Conceptual Role | Proposed Name | Why? |
| :--- | :--- | :--- |
| **Survey** | **`code_outline`** | Returns a collapsed "IDE view" (not just signatures). |
| **Inspect** | **`inspect_symbol`** | Deep dive: implementation + recursive definition (depth=1). |
| **Docs** | **`read_docs`** | Returns Godoc format (works for internal & external). |
| **Edit** | **`smart_edit`** | Intelligent editing with `gofmt` normalization & autofix. |
| **Refactor** | **`rename_symbol`** | Explicit semantic renaming. |
| **Upgrade** | **`analyze_dependency_updates`** | Checks dependency updates for API breaking changes. |
| **Modernize**| **`modernize_code`** | Applies modern Go patterns (e.g., `slices.Sort`). |
| **Explore** | **`list_files`** | Native file listing (includes GOMODCACHE support). |
| **Build** | **`go_build`** | Dedicated build verification. |
| **Test** | **`go_test`** | Dedicated test runner. |
| **Architecture** | **`analyze_project`**| High-level project map/summary. |
| **Analysis** | **`find_references`**| Impact analysis helper. |
| **Scaffold** | **`implement_stub`** | Boilerplate generation. |

## 4. Refactoring Plans: "The Context-Aware Suite" (Plan A)

**Philosophy:** Tools are "Semantic Accessors" that provide a comparative advantage over text tools (Token efficiency, Safety, Grounding).

### 4.1 Tool Specifications (Pydoc Style)

#### `code_outline`
*   **Description:** Returns the file content with function/struct bodies collapsed (like an IDE). Useful for low-cost navigation.
*   **Arguments:** `file` (string).
*   **Returns:** File skeleton + Appendix with docs for external imports.

#### `inspect_symbol`
*   **Description:** Returns the full source code of a symbol, PLUS context (recursive depth=1). Best for grounding edits.
*   **Arguments:** `symbol` (string), `package` (optional string), `file` (optional string).
*   **Returns:** Source code, doc comments, and referenced type definitions (1 level deep).

#### `read_docs`
*   **Description:** Returns documentation in Godoc format. Works for both internal project packages and external dependencies (even if no local files exist).
*   **Arguments:** `package` (string), `symbol` (optional string).
*   **Returns:** Godoc output (docs + signatures + examples).

#### `smart_edit`
*   **Description:** Edits code using fuzzy matching and safety checks. Normalizes both content and search context using `gofmt` to ignore whitespace differences.
*   **Arguments:**
    *   `file` (string)
    *   `search_context` (string): Unique code block to replace.
    *   `replacement` (string): New code.
    *   `match_threshold` (float, default 0.95): Confidence required for match.
    *   `autofix_threshold` (float, default 0.95): If match < threshold but > autofix, report "Did you mean?".
*   **Returns:** Success message or detailed Error (syntax/build failure) with recommendations.

#### `rename_symbol`
*   **Description:** Safely renames a symbol and updates all references in the codebase.
*   **Arguments:** `target_symbol` (string), `new_name` (string).

#### `analyze_dependency_updates`
*   **Description:** Checks for API compatibility issues when upgrading dependencies. Uses `apidiff` to detect breaking changes between current and target versions.
*   **Arguments:** `dependency` (string, optional - checks all if empty), `target_version` (string, optional).
*   **Returns:** Risk assessment report (Low/High risk) with specific API changes (Incompatible/Compatible).

#### `modernize_code`
*   **Description:** Analyzes code and suggests/applies modern Go patterns (e.g., replacing loops with `slices.Contains`, using `min/max`).
*   **Arguments:** `path` (string, default "."), `fix` (bool, default false).
*   **Returns:** List of suggested modernizations or confirmation of applied fixes.

#### `list_files`
*   **Description:** Lists files in a directory. Can look into GOMODCACHE.
*   **Arguments:** `dir` (string), `recursive` (bool, default false).

#### `go_build`
*   **Description:** Runs `go build` on the package.
*   **Arguments:** `package_path` (optional, default "." in current dir).

#### `go_test`
*   **Description:** Runs `go test` on the package.
*   **Arguments:** `package_path` (optional), `run_regex` (optional).

#### `analyze_project`
*   **Description:** Returns a high-level map of the project structure and key packages.
*   **Arguments:** None.

#### `find_references`
*   **Description:** Find all usages of a specific symbol.
*   **Arguments:** `symbol`, `package` (optional).

#### `implement_stub`
*   **Description:** Generates checking code to ensure a struct implements an interface, or scaffolds missing methods.
*   **Arguments:** `struct_name`, `interface_name`.

---

## 5. Client Instructions (System Prompt Addendum)

The following instructions guide the agent to use `godoctor` for its advantages (Token Saving, Safety, Accuracy).

```markdown
## Go Smart Tooling Guide

### 🔍 Navigation: Save Tokens & Context
*   **`code_outline`**: PREFER this over `read_file`. It gives you the file structure (like a folded IDE view) using 90% fewer tokens.
*   **`inspect_symbol`**: Use this to get the **Ground Truth** for code you plan to edit. It returns the exact implementation AND definitions of related types (fields, structs), ensuring your edit fits perfectly.
*   **`list_files`**: Use this to explore standard library or external module files if needed.

### ✏️ Editing: Ensure Safety
*   **`smart_edit`**: Use this for all code modifications.
    *   **Whitespace Agnostic:** It normalizes code using `gofmt`, so distinct indentations match.
    *   **Pre-Verification:** It runs `goimports` and syntax checks *before* saving. It detects broken builds immediately.
    *   **Auto-Fix:** It fixes small typos in your `search_context` to avoid retries.

### 🚀 Modernization & Upgrades
*   **`analyze_dependency_updates`**: Run this BEFORE upgrading dependencies to catch breaking API changes (Risk Assessment).
*   **`modernize_code`**: Run this to automatically upgrade old patterns (e.g. `interface{}` -> `any`, manual loops -> `slices`).

### 🛠️ Utilities
*   **`go_build`**: Run this after a sequence of edits to ensure the whole project compiles.
*   **`go_test`**: Run specific tests to verify logic.
*   **`analyze_project`**: Use this first when joining a new project to get a mental map.
```

## 6. Implementation Roadmap

1.  **Phase 1: Core Refactor (v0.8.1)**
    *   Implement `code_outline`.
    *   Update `inspect_symbol` (Depth=1).
    *   Update `smart_edit` (Thresholds 0.95, `gofmt`).
2.  **Phase 2: Modernization Suite**
    *   Implement `analyze_dependency_updates` (wrapping `apidiff`).
    *   Implement `modernize_code` (wrapping `modernize` analyzer).
3.  **Phase 3: Expanded Toolset**
    *   Add `rename_symbol`, `list_files`, `go_build`, `go_test`.
    *   Add `analyze_project`, `find_references`, `implement_stub`.

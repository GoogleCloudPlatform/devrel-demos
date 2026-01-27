# The Evolution of GoDoctor Tools

This document traces the history and architectural shifts of the GoDoctor project, from a simple documentation wrapper to a comprehensive AI-powered Go engineering suite.

## 1. Timeline of Tool Evolution

| Era | Key Changes & Focus | Tools Available |
| :--- | :--- | :--- |
| **Genesis** | Basic implementation. | `getDoc` |
| **Standardization** | Aligning with standard Go tools. | `go-doc`, `godoc`, `code_review` |
| **Expansion** | Adding file editing and formatting. | `godoc`, `code_review`, `goimports`, `gopretty` |
| **Creation** | Ability to write new files. | `godoc`, `code_review`, `gopretty`, `scribble` |
| **Refinement** | Surgical editing introduced. | `godoc`, `code_review`, `scribble`, `scalpel` |
| **Exploration** | Web crawling capabilities (short-lived). | `godoc`, `code_review`, `scribble`, `scalpel`, `endoscope` |
| **Renaming** | Major semantic renaming for clarity. | `get_documentation`, `review_code`, `write_code`, `edit_code`, `fetch_webpage` |
| **Focus** | Dropping web tools to focus on Code. | `get_docs`, `code_review` |
| **Modern Era** | The "Agentic" Shift. Massive expansion. | **15+ Tools** including `file_edit`, `symbol_inspect`, `go_docs` |
| **Extension** | Native Gemini CLI integration & Specialist Skills. | `go-architect`, `go-test-expert`, `go-backend-dev`, `go-reviewer` |

## 2. Architectural Shifts

### From Surgical to Intelligent
Early versions of the tool used "Surgical" metaphors (`scalpel`, `scribble`) and relied on exact string matching. The project evolved toward **Intelligence** with tools like `file_edit` (fuzzy matching) and `go_modernize` (AST-aware refactoring).

### The Identity of Documentation
The project's core feature—documentation retrieval—went through six major renames to optimize LLM performance:
`getDoc` → `go-doc` → `godoc` → `get_docs` → `read_godoc` → `read_docs` → **`go_docs`**.

### The "Agentic" Turn
The most significant shift was the introduction of the **Semantic Toolset**. Instead of providing a flat list of tools, GoDoctor now features specialized domain groups:
*   **`file_*`**: Core file operations and surgical editing.
*   **`go_*`**: Toolchain integration.
*   **`symbol_*`**: Deep semantic inspection and refactoring.

### The Skill Layer
With the introduction of the Gemini CLI Extension, GoDoctor moved beyond tools to providing **Expertise**. The `skills/` directory allows the agent to adopt specific personas (`go-architect`, `go-test-expert`) with deep, curated knowledge about the SDLC, preventing hallucinations and enforcing best practices like ADRs and quality gates.

---

## Appendix: Raw History Analysis

### COMMIT: d47a5d7 (Initial Implementation)
- **getDoc**: symbol (string)

### COMMIT: e7e944a (Go Doc Integration)
- **go-doc**: package_path (string), SymbolName (string)
- **code_review**: expert review logic introduced.

### COMMIT: c68e4d0 (Refactoring & Imports)
- **godoc**: package_path (string), SymbolName (string)
- **goimports**: file_path (string)
- **code_review**: file_content (string), ModelName (string), Hint (string)

### COMMIT: f8a8f03 (File Creation)
- **scribble**: file_path (string), content (string)

### COMMIT: 10e7069 (Surgical Edits)
- **scalpel**: file_path (string), old_string (string), new_string (string)

### COMMIT: 26229ce (The Web Experiment)
- **endoscope**: url (string), level (int), external (bool)

### COMMIT: 97b6ae3 (Semantic Renaming Phase 1)
- **fetch_webpage** (formerly endoscope)
- **get_documentation** (formerly godoc)
- **write_code** (formerly scribble)
- **edit_code** (formerly scalpel)

### COMMIT: 7fb360db (Bulk Edits)
- **edit_code**: edits ([]Edit) - shifted from single string to slice of replacements.

### COMMIT: 1263cdc (File Inspection)
- **inspect_file**: code-aware registration of symbols.

### COMMIT: 9961068 (Modern Era / Semantic Alignment)
- **file_edit**: Fuzzy matching editor (formerly smart_edit).
- **go_docs**: Documentation retrieval (formerly read_docs).
- **go_modernize**: AST-based refactoring (formerly modernize).
- **symbol_inspect**: Deep semantic inspection (formerly inspect_symbol).
- **go_diff**: API breaking change detection (formerly analyze_dependency_updates).
- **file_list / file_outline / file_read**: Navigation suite.
- **go_build / go_test / go_get**: Toolchain integration.
- **symbol_rename**: Semantic refactoring.
- **safe_shell**: Secure command execution.
- **code_review**: Expert analysis.

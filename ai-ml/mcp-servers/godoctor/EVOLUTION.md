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
| **Modern Era** | The "Agentic" Shift. Massive expansion. | **18+ Tools** including `ask_the_master_gopher`, `ask_specialist`, `smart_edit` |

## 2. Architectural Shifts

### From Surgical to Intelligent
Early versions of the tool used "Surgical" metaphors (`scalpel`, `scribble`) and relied on exact string matching. The project evolved toward **Intelligence** with tools like `smart_edit` (fuzzy matching) and `modernize` (AST-aware refactoring).

### The Identity of Documentation
The project's core feature—documentation retrieval—went through five major renames to optimize LLM performance:
`getDoc` → `go-doc` → `godoc` → `get_docs` → `read_godoc` → **`read_docs`**.

### The "Agentic" Turn
The most significant shift was the introduction of the **Meta-Layer**. Instead of providing a flat list of tools, GoDoctor now features:
*   **`ask_the_master_gopher`**: A dynamic gateway that unlocks other tools based on user intent.
*   **`ask_specialist`**: An autonomous investigator.

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

### COMMIT: 9961068 (Modern Era / Restore)
- **ask_the_master_gopher**: Meta-agent gateway.
- **smart_edit**: Fuzzy matching editor.
- **read_docs**: High-level module mapping.
- **modernize**: AST-based refactoring.
- **inspect_symbol**: Deep semantic inspection.
- **analyze_dependency_updates**: API breaking change detection.
- **go_build / go_test / go_install**: Toolchain integration.
- **ask_specialist**: Investigative agent.
- **list_files / open / read_code / code_outline**: Navigation suite.

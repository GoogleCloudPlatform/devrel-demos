// Package toolnames defines the registry of available tools for the godoctor server.
// It serves as a centralized catalog containing metadata (Name, Title, Description, Instructions)
// for each tool, which is used to advertise capabilities to the MCP client and guide the LLM.
package toolnames

// ToolDef defines the textual representation of a tool.
type ToolDef struct {
	Name        string // The canonical name (e.g. "file_create")
	Title       string // Human-readable title
	Description string // Description passed to the LLM via MCP
	Instruction string // Guidance for the system prompt
}

// Registry holds all tool definitions, keyed by Name.
var Registry = map[string]ToolDef{
	// --- FILE OPERATIONS ---
	"file_create": {
		Name:        "file_create",
		Title:       "Create File",
		Description: "Initializes a new source file, automatically creating parent directories and applying standard Go formatting. Ensures new files are immediately compliant with project style guides.",
		Instruction: "*   **`file_create`**: Initialize a new source file.\n    *   **Usage:** `file_create(filename=\"cmd/main.go\", content=\"package main\n...\")`\n    *   **Outcome:** A correctly formatted, directory-synced file is created.",
	},
	"smart_edit": {
		Name:        "smart_edit",
		Title:       "Smart Edit",
		Description: "An intelligent file editor providing robust block matching and safety guarantees. Automatically handles formatting (gofmt), import optimization, and syntax verification to ensure edits do not break the build.",
		Instruction: "*   **`smart_edit`**: The primary tool for safe code modification.\n    *   **Capabilities:** Validates syntax and auto-formats (gofmt/goimports) *before* committing changes to disk.\n    *   **Robustness:** Uses fuzzy matching to locate target blocks despite minor whitespace or indentation variances.\n    *   **Usage:** `smart_edit(filename=\"...\", old_content=\"...\", new_content=\"...\")`.\n    *   **Append Mode:** Leave `old_content` empty to append to the end of the file.\n    *   **Outcome:** A syntactically valid, properly formatted file update.",
	},
	"smart_read": {
		Name:        "smart_read",
		Title:       "Read File",
		Description: "A structure-aware file reader that optimizes for context density. Supports returning full content, structural outlines (signatures only), or specific line ranges to minimize token consumption.",
		Instruction: "*   **`smart_read`**: Inspect file content and structure.\n    *   **Read All:** `smart_read(filename=\"pkg/utils.go\")`\n    *   **Outline:** `smart_read(filename=\"pkg/utils.go\", outline=true)` (Retrieve types and function signatures only).\n    *   **Snippet:** `smart_read(filename=\"pkg/utils.go\", start_line=10, end_line=50)` (Targeted range reading).\n    *   **Outcome:** Targeted source content or structural map.",
	},
	"list_files": {
		Name:        "list_files",
		Title:       "List Files",
		Description: "Recursively lists files and directories while filtering out build artifacts and version control data (e.g., .git, node_modules). Provides an accurate view of the source code hierarchy.",
		Instruction: "*   **`list_files`**: Explore the project structure.\n    *   **Usage:** `list_files(path=\".\", depth=2)`\n    *   **Outcome:** A hierarchical list of source files and directories.",
	},

	// --- DOCS ---
	"read_docs": {
		Name:        "read_docs",
		Title:       "Get Documentation",
		Description: "Retrieves authoritative Go documentation for any package or symbol. Streamlines development by providing API signatures and usage examples directly within the workflow.",
		Instruction: "*   **`read_docs`**: Access API documentation.\n    *   **Usage:** `read_docs(import_path=\"net/http\")`\n    *   **Outcome:** API reference and usage guidance.",
	},

	// --- GO TOOLCHAIN ---
	"verify_build": {
		Name:        "verify_build",
		Title:       "Verify Build",
		Description: "Compiles packages and dependencies to identify syntax and type-checking errors. Provides structured diagnostic reports with embedded source context for efficient error resolution.",
		Instruction: "*   **`verify_build`**: Validate compilation integrity.\n    *   **Usage:** `verify_build(packages=[\"./...\"])`\n    *   **Outcome:** Build status report with precise error diagnostics.",
	},
	"verify_tests": {
		Name:        "verify_tests",
		Title:       "Run Tests",
		Description: "Executes the package test suite and generates a structured summary of results. Includes per-package coverage analysis to help identify untested logic paths.",
		Instruction: "*   **`verify_tests`**: Verify logical correctness and code coverage.\n    *   **Usage:** `verify_tests(packages=[\"./pkg/...\"], run=\"TestAuth\")`\n    *   **Outcome:** Structured test results (PASS/FAIL/SKIP) and coverage data.",
	},
	"add_dependency": {
		Name:        "add_dependency",
		Title:       "Add Dependency",
		Description: "Manages Go module installation and manifest updates. Consolidates the workflow by immediately returning the public API documentation for the installed packages.",
		Instruction: "*   **`add_dependency`**: Install dependencies and fetch documentation.\n    *   **Usage:** `add_dependency(packages=[\"github.com/gin-gonic/gin@latest\"])`\n    *   **Outcome:** Dependency added to go.mod and API documentation returned.",
	},
	"modernize_code": {
		Name:        "modernize_code",
		Title:       "Modernize Code",
		Description: "Analyzes the codebase for outdated Go patterns and automatically refactors them to modern standards. Improves maintainability and performance by applying idiomatic upgrades.",
		Instruction: "*   **`modernize_code`**: Automatically upgrade legacy patterns.\n    *   **Usage:** `modernize_code(dir=\".\", fix=true)`\n    *   **Outcome:** Source code refactored to modern Go standards.",
	},
	"check_api": {
		Name:        "check_api",
		Title:       "Check API Compatibility",
		Description: "Compares the public API of two package versions to detect breaking changes. Essential for maintaining backward compatibility and adhering to semantic versioning.",
		Instruction: "*   **`check_api`**: Identify breaking changes in the public API.\n    *   **Usage:** `check_api(old=\"v1.0.0\", new=\".\")`\n    *   **Outcome:** Report on incompatible API changes.",
	},

	// --- AGENTS ---
	"code_review": {
		Name:        "code_review",
		Title:       "Code Review",
		Description: "Provides an automated architectural and idiomatic review of source code. Identifies potential defects in concurrency, error handling, and performance before code is committed.",
		Instruction: "*   **`code_review`**: Perform an automated expert review.\n    *   **Usage:** `code_review(file_content=\"...\")`\n    *   **Outcome:** A structured critique identifying potential bugs and optimization opportunities.",
	},
}

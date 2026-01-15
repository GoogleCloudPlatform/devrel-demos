package toolnames

// ToolDef defines the textual representation of a tool.
type ToolDef struct {
	Name        string // The internal name used by the tool registry
	Title       string // Human-readable title
	Description string // Description passed to the LLM via MCP
	Instruction string // Guidance for the system prompt
	Experimental bool   // Whether the tool is considered experimental
}

// Registry holds all tool definitions.
var Registry = map[string]ToolDef{
	// 1. write
	"write": {
		Name:        "write",
		Title:       "Write New Go File",
		Description: "Create a new Go file with automatic directory creation and import management. Use ONLY for creating new files.",
		Instruction: "*   **`write`**: Use this to create NEW Go files. For existing files, use `smart_edit`.",
		Experimental: true,
	},
	// 2. code_outline
	"code_outline": {
		Name:        "code_outline",
		Title:       "Code Outline",
		Description: "Scan a Go file to reveal its structure (imports, types, function signatures) without reading the full body. Use this to quickly understand file contents while saving context window space.",
		Instruction: "*   **`code_outline`**: PREFER this over `read_file`. It gives you the file structure (like a folded IDE view) using 90% fewer tokens.",
		Experimental: true,
	},
	// 3. smart_edit
	"smart_edit": {
		Name:        "smart_edit",
		Title:       "Smart Edit (Fuzzy Patch)",
		Description: "The comprehensive Go editor. Supports two modes: 1) **Modify**: Provide `search_context` to locate and replace code (fuzzy match). 2) **Append**: Leave `search_context` empty to add code to the end of the file. Always verifies compilation.",
		Instruction: "*   **`smart_edit`**: Use this for all code modifications.\n    *   **Modify:** Provide `search_context` to replace code.\n    *   **Append:** Leave `search_context` empty to add new code (e.g. new functions).\n    *   **Safety:** Automatically runs `goimports` and checks syntax.",
		Experimental: true,
	},
	// 4. go_build
	"go_build": {
		Name:        "go_build",
		Title:       "Go Build",
		Description: "Compile the project or specific packages. Use this to verify that your changes have not introduced build errors across the entire module.",
		Instruction: "*   **`go_build`**: Run this after a sequence of edits to ensure the whole project compiles.",
		Experimental: true,
	},
	// 5. go_test
	"go_test": {
		Name:        "go_test",
		Title:       "Go Test",
		Description: "Run Go tests with support for specific packages or regex matching. Use this to verify logic correctness and prevent regressions.",
		Instruction: "*   **`go_test`**: Run specific tests to verify logic.",
		Experimental: true,
	},
	// 6. go_install
	"go_install": {
		Name:        "go_install",
		Title:       "Go Install",
		Description: "Install a Go package or binary. Use this to add dependencies or tools to the environment.",
		Instruction: "*   **`go_install`**: Use this to install packages.",
		Experimental: true,
	},
	// 7. inspect_symbol
	"inspect_symbol": {
		Name:        "inspect_symbol",
		Title:       "Inspect Symbol",
		Description: "Deep dive into a specific symbol (function, type, var). Returns the exact source code definition, documentation, and references. Essential for understanding implementation details before refactoring.",
		Instruction: "*   **`inspect_symbol`**: Use this to get the **Ground Truth** for code you plan to edit. It returns the exact implementation AND definitions of related types (fields, structs), ensuring your edit fits perfectly.",
		Experimental: true,
	},
	// 8. list_files
	"list_files": {
		Name:        "list_files",
		Title:       "List Files",
		Description: "Explore the project file structure recursively. Use this to discover files, understand project layout, and locate relevant code modules.",
		Instruction: "*   **`list_files`**: Use this to explore standard library or external module files if needed.",
		Experimental: true,
	},
	// 9. open
	"open": {
		Name:        "open",
		Title:       "Open File (Satellite View)",
		Description: "Get a high-level 'Satellite View' of a file. Returns imports and top-level declarations (skeleton). Use this first to assess a file's purpose before reading detailed code.",
		Instruction: "*   **`open`**: Returns the skeleton (imports & signatures) of a local file. Perfect for a quick survey before editing.",
		Experimental: true,
	},
	// 10. read_docs
	"read_docs": {
		Name:        "read_docs",
		Title:       "Read Documentation",
		Description: "Map the project's architecture. Returns a structured overview of a package's exported API and sub-packages. Use this to navigate large codebases and find relevant functionality.",
		Instruction: "*   **`read_docs`**: Efficiently lists sub-packages and exported symbols.",
		Experimental: false,
	},
	// 11. analyze_dependency_updates
	"analyze_dependency_updates": {
		Name:        "analyze_dependency_updates",
		Title:       "Analyze Dependency Updates",
		Description: "Risk assessment for dependency upgrades. Checks for breaking API changes (incompatible exports) between versions using `apidiff`.",
		Instruction: "*   **`analyze_dependency_updates`**: Run this BEFORE upgrading dependencies to catch breaking API changes (Risk Assessment).",
		Experimental: true,
	},
	// 12. modernize
	"modernize": {
		Name:        "modernize",
		Title:       "Modernize Go Code",
		Description: "Modernize legacy Go code. Automatically detects and upgrades patterns to use newer Go features (e.g., modern loops, `any` type, slice helpers).",
		Instruction: "*   **`modernize`**: Run this to automatically upgrade old patterns (e.g. `interface{}` -> `any`, manual loops -> `slices`).",
		Experimental: true,
	},
	// 13. ask_specialist
	"ask_specialist": {
		Name:        "ask_specialist",
		Title:       "Ask Specialist",
		Description: "Delegate investigation to an autonomous agent. The Specialist can search, read, and test independently to answer complex questions like 'How does auth work?' or 'Find the root cause of this error'.",
		Instruction: "*   **`ask_specialist`**: Use this if you are stuck or need access to more tools. DONT hallucinate tools, ask the specialist to provide them.",
		Experimental: false,
	},
	// 14. ask_the_master_gopher
	"ask_the_master_gopher": {
		Name:        "ask_the_master_gopher",
		Title:       "Ask The Master Gopher",
		Description: "Consult the project lead. The Master Gopher understands your intent and dynamically unlocks the necessary tools for your task. Use this when you are unsure how to proceed.",
		Instruction: "*   **`ask_the_master_gopher`**: Use this when you are unsure which tool to use or how to solve a problem. The Master will review your request, unlock appropriate capabilities in the server, and give you wise instructions.",
		Experimental: true,
	},
	// 15. edit_code (Fallback)
	"edit_code": {
		Name:        "edit_code",
		Title:       "Edit Code",
		Description: "Smartly edits a Go file (*.go) with fuzzy matching and safety checks.",
		Instruction: "*   **`edit_code`**: Modifies files using fuzzy matching context.",
		Experimental: false,
	},
	// 16. read_code
	"read_code": {
		Name:        "read_code",
		Title:       "Read Code",
		Description: "Read the full content of a Go file and extract a symbol table. Use this when you need to examine the complete implementation logic of a file.",
		Instruction: "*   **`read_code`**: Reads a Go file (*.go) and extracts a symbol table (functions, types, variables).",
		Experimental: false,
	},
	// 17. rename_symbol
	"rename_symbol": {
		Name:        "rename_symbol",
		Title:       "Rename Symbol",
		Description: "Safe, semantic refactoring. Renames a symbol and updates all references across the codebase using `gopls`. Prevents broken references.",
		Instruction: "*   **`rename_symbol`**: Renames a symbol refactoring-style using 'gopls'. Updates all references safely.",
		Experimental: true,
	},
	// 18. review_code
	"review_code": {
		Name:        "review_code",
		Title:       "Review Go Code",
		Description: "Request an AI code review. Analyzes code for correctness, idiomatic Go style, and potential bugs. Use this before finalizing changes.",
		Instruction: "*   **`review_code`**: Reviews Go code for correctness, style, and idiomatic usage.",
		Experimental: true,
	},
	// 19. analyze_project (Placeholder/Virtual)
	"analyze_project": {
		Name:        "analyze_project",
		Title:       "Analyze Project",
		Description: "Use this first when joining a new project to get a mental map.",
		Instruction: "*   **`analyze_project`**: Use this first when joining a new project to get a mental map.",
		Experimental: true,
	},
}
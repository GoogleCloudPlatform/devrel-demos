package toolnames

// ToolDef defines the textual representation of a tool.
type ToolDef struct {
	InternalName string // The immutable internal identifier (e.g. "file.create")
	ExternalName string // The name exposed to the Agent (e.g. "write")
	Title        string // Human-readable title
	Description  string // Description passed to the LLM via MCP
	Instruction  string // Guidance for the system prompt
	Experimental bool   // Whether the tool is considered experimental
}

// ToolConfigEntry defines the structure for overriding a tool's definition in the config file.
type ToolConfigEntry struct {
	ExternalName string `json:"name" yaml:"name"`
	Title        string `json:"title" yaml:"title"`
	Description  string `json:"description" yaml:"description"`
	Instruction  string `json:"instruction" yaml:"instruction"`
}

// ApplyOverrides updates the registry with values from the provided map.
func ApplyOverrides(overrides map[string]ToolConfigEntry) {
	for internalName, override := range overrides {
		if original, ok := Registry[internalName]; ok {
			if override.ExternalName != "" {
				original.ExternalName = override.ExternalName
			}
			if override.Title != "" {
				original.Title = override.Title
			}
			if override.Description != "" {
				original.Description = override.Description
			}
			if override.Instruction != "" {
				original.Instruction = override.Instruction
			}
			Registry[internalName] = original
		}
	}
}

// Registry holds all tool definitions, keyed by InternalName.
var Registry = map[string]ToolDef{
	// --- FILE OPERATIONS ---
	"file.create": {
		InternalName: "file.create",
		ExternalName: "write",
		Title:        "Write New Go File",
		Description:  "Create a new Go file with automatic directory creation and import management. Use ONLY for creating new files.",
		Instruction:  "*   **`write`**: Use this to create NEW Go files. For existing files, use `smart_edit`.",
		Experimental: true,
	},
	"file.edit": {
		InternalName: "file.edit",
		ExternalName: "smart_edit",
		Title:        "Smart Edit (Fuzzy Patch)",
		Description:  "The comprehensive Go editor. Supports two modes: 1) **Modify**: Provide `search_context` to locate and replace code (fuzzy match). 2) **Append**: Leave `search_context` empty to add code to the end of the file. Always verifies compilation.",
		Instruction:  "*   **`smart_edit`**: Use this for all code modifications.\n    *   **Modify:** Provide `search_context` to replace code.\n    *   **Append:** Leave `search_context` empty to add new code (e.g. new functions).\n    *   **Safety:** Automatically runs `goimports` and checks syntax.",
		Experimental: true,
	},
	"file.outline": {
		InternalName: "file.outline",
		ExternalName: "code_outline",
		Title:        "Code Outline",
		Description:  "Scan a Go file to reveal its structure (imports, types, function signatures) without reading the full body. Use this to quickly understand file contents while saving context window space.",
		Instruction:  "*   **`code_outline`**: PREFER this over `read_code`. It gives you the file structure (like a folded IDE view) using 90% fewer tokens.",
		Experimental: true,
	},
	"file.read": {
		InternalName: "file.read",
		ExternalName: "read_code",
		Title:        "Read Code",
		Description:  "Read the full content of a Go file and extract a symbol table. Use this when you need to examine the complete implementation logic of a file.",
		Instruction:  "*   **`read_code`**: Reads a Go file (*.go) and extracts a symbol table (functions, types, variables).",
		Experimental: false,
	},
	"file.list": {
		InternalName: "file.list",
		ExternalName: "list_files",
		Title:        "List Files",
		Description:  "Explore the project file structure recursively. Use this to discover files, understand project layout, and locate relevant code modules.",
		Instruction:  "*   **`list_files`**: Use this to explore standard library or external module files if needed.",
		Experimental: true,
	},

	// --- SYMBOL OPERATIONS ---
	"symbol.inspect": {
		InternalName: "symbol.inspect",
		ExternalName: "inspect_symbol",
		Title:        "Inspect Symbol",
		Description:  "Deep dive into a specific symbol (function, type, var). Returns the exact source code definition, documentation, and references. Essential for understanding implementation details before refactoring.",
		Instruction:  "*   **`inspect_symbol`**: Use this to get the **Ground Truth** for code you plan to edit. It returns the exact implementation AND definitions of related types (fields, structs), ensuring your edit fits perfectly.",
		Experimental: true,
	},
	"symbol.rename": {
		InternalName: "symbol.rename",
		ExternalName: "rename_symbol",
		Title:        "Rename Symbol",
		Description:  "Safe, semantic refactoring. Renames a symbol and updates all references across the codebase using `gopls`. Prevents broken references.",
		Instruction:  "*   **`rename_symbol`**: Renames a symbol refactoring-style using 'gopls'. Updates all references safely.",
		Experimental: true,
	},

	// --- PROJECT & DOCS ---
	"project.map": {
		InternalName: "project.map",
		ExternalName: "analyze_project",
		Title:        "Analyze Project",
		Description:  "Use this first when joining a new project to get a mental map.",
		Instruction:  "*   **`analyze_project`**: Use this first when joining a new project to get a mental map.",
		Experimental: false,
	},
	"go.docs": {
		InternalName: "go.docs",
		ExternalName: "read_docs",
		Title:        "Read Documentation",
		Description:  "Map the project's architecture. Returns a structured overview of a package's exported API and sub-packages. Use this to navigate large codebases and find relevant functionality.",
		Instruction:  "*   **`read_docs`**: Efficiently lists sub-packages and exported symbols.",
		Experimental: false,
	},

	// --- GO TOOLCHAIN ---
	"go.build": {
		InternalName: "go.build",
		ExternalName: "go_build",
		Title:        "Go Build",
		Description:  "Compile the project or specific packages. Use this to verify that your changes have not introduced build errors across the entire module.",
		Instruction:  "*   **`go_build`**: Run this after a sequence of edits to ensure the whole project compiles.",
		Experimental: true,
	},
	"go.test": {
		InternalName: "go.test",
		ExternalName: "go_test",
		Title:        "Go Test",
		Description:  "Run Go tests with support for specific packages or regex matching. Use this to verify logic correctness and prevent regressions.",
		Instruction:  "*   **`go_test`**: Run specific tests to verify logic.",
		Experimental: true,
	},
	"go.install": {
		InternalName: "go.install",
		ExternalName: "go_install",
		Title:        "Go Install",
		Description:  "Install a Go package or binary. Use this to add dependencies or tools to the environment.",
		Instruction:  "*   **`go_install`**: Use this to install packages.",
		Experimental: true,
	},
	"go.modernize": {
		InternalName: "go.modernize",
		ExternalName: "modernize",
		Title:        "Modernize Go Code",
		Description:  "Modernize legacy Go code. Automatically detects and upgrades patterns to use newer Go features (e.g., modern loops, `any` type, slice helpers).",
		Instruction:  "*   **`modernize`**: Run this to automatically upgrade old patterns (e.g. `interface{}` -> `any`, manual loops -> `slices`).",
		Experimental: true,
	},
	"go.diff": {
		InternalName: "go.diff",
		ExternalName: "analyze_dependency_updates",
		Title:        "Analyze Dependency Updates",
		Description:  "Risk assessment for dependency upgrades. Checks for breaking API changes (incompatible exports) between versions using `apidiff`.",
		Instruction:  "*   **`analyze_dependency_updates`**: Run this BEFORE upgrading dependencies to catch breaking API changes (Risk Assessment).",
		Experimental: true,
	},

	// --- AGENTS ---
	"agent.review": {
		InternalName: "agent.review",
		ExternalName: "review_code",
		Title:        "Review Go Code",
		Description:  "Request an AI code review. Analyzes code for correctness, idiomatic Go style, and potential bugs. Use this before finalizing changes.",
		Instruction:  "*   **`review_code`**: Reviews Go code for correctness, style, and idiomatic usage.",
		Experimental: true,
	},
	"agent.specialist": {
		InternalName: "agent.specialist",
		ExternalName: "ask_specialist",
		Title:        "Ask Specialist",
		Description:  "Delegate investigation to an autonomous agent. The Specialist can search, read, and test independently to answer complex questions like 'How does auth work?' or 'Find the root cause of this error'.",
		Instruction:  "*   **`ask_specialist`**: Use this if you are stuck or need access to more tools. DONT hallucinate tools, ask the specialist to provide them.",
		Experimental: false,
	},
	"agent.master": {
		InternalName: "agent.master",
		ExternalName: "ask_the_master_gopher",
		Title:        "Ask The Master Gopher",
		Description:  "Consult the project lead. The Master Gopher understands your intent and dynamically unlocks the necessary tools for your task. Use this when you are unsure how to proceed.",
		Instruction:  "*   **`ask_the_master_gopher`**: Use this when you are unsure which tool to use or how to solve a problem. The Master will review your request, unlock appropriate capabilities in the server, and give you wise instructions.",
		Experimental: true,
	},
	
	// --- LEGACY/FALLBACK ---
	"file.edit_legacy": {
		InternalName: "file.edit_legacy",
		ExternalName: "edit_code",
		Title:        "Edit Code",
		Description:  "Smartly edits a Go file (*.go) with fuzzy matching and safety checks.",
		Instruction:  "*   **`edit_code`**: Modifies files using fuzzy matching context.",
		Experimental: false,
	},
}
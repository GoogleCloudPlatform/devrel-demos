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
		ExternalName: "file.create",
		Title:        "Create File",
		Description:  "Creates a new file at the specified path with the provided content. Automatically creates parent directories if they do not exist. Runs `goimports` to format the code and manage imports before saving. Defaults to overwrite mode.",
		Instruction:  "*   **`file.create`**: Use this to create NEW Go files. For existing files, use `file.edit`.",
		Experimental: true,
	},
	"file.edit": {
		InternalName: "file.edit",
		ExternalName: "file.edit",
		Title:        "Edit File (Smart)",
		Description:  "Modifies an existing Go file using fuzzy matching or appending. If `search_context` is provided, locates the block with the highest similarity score and replaces it. If `search_context` is empty, appends content to the end. Automatically formats code using `goimports` and verifies syntax before saving.",
		Instruction:  "*   **`file.edit`**: Use this for all code modifications.\n    *   **Modify:** Provide `search_context` to replace code.\n    *   **Append:** Leave `search_context` empty to add new code (e.g. new functions).\n    *   **Safety:** Automatically runs `goimports` and checks syntax.",
		Experimental: true,
	},
	"file.outline": {
		InternalName: "file.outline",
		ExternalName: "file.outline",
		Title:        "File Outline",
		Description:  "Parses a Go source file and returns a skeleton containing imports, type definitions, and function signatures. Does not include function bodies. Useful for quickly assessing file structure with minimal token usage.",
		Instruction:  "*   **`file.outline`**: PREFER this over `file.read`. It gives you the file structure (like a folded IDE view) using 90% fewer tokens.",
		Experimental: true,
	},
	"file.read": {
		InternalName: "file.read",
		ExternalName: "file.read",
		Title:        "Read File",
		Description:  "Reads and returns the complete content of a Go source file. Additionally extracts and lists a symbol table containing functions, types, and variables defined in the file.",
		Instruction:  "*   **`file.read`**: Reads a Go file (*.go) and extracts a symbol table (functions, types, variables).",
		Experimental: false,
	},
	"file.list": {
		InternalName: "file.list",
		ExternalName: "file.list",
		Title:        "List Files",
		Description:  "Recursively lists files and directories starting from a specified root path. Supports depth limiting to manage output size.",
		Instruction:  "*   **`file.list`**: Use this to explore standard library or external module files if needed.",
		Experimental: true,
	},

	// --- SYMBOL OPERATIONS ---
	"symbol.inspect": {
		InternalName: "symbol.inspect",
		ExternalName: "symbol.inspect",
		Title:        "Inspect Symbol",
		Description:  "Retrieves detailed information for a specific Go symbol, including its signature, source code definition, and documentation comments. Resolves symbols using the project's knowledge graph.",
		Instruction:  "*   **`symbol.inspect`**: Use this to get the **Ground Truth** for code you plan to edit. It returns the exact implementation AND definitions of related types (fields, structs), ensuring your edit fits perfectly.",
		Experimental: true,
	},
	"symbol.rename": {
		InternalName: "symbol.rename",
		ExternalName: "symbol.rename",
		Title:        "Rename Symbol",
		Description:  "Renames a Go identifier (function, type, variable) and updates all references throughout the codebase using the `gopls` tool to ensure semantic correctness.",
		Instruction:  "*   **`symbol.rename`**: Renames a symbol refactoring-style using 'gopls'. Updates all references safely.",
		Experimental: true,
	},

	// --- PROJECT & DOCS ---
	"project.map": {
		InternalName: "project.map",
		ExternalName: "project.map",
		Title:        "Project Map",
		Description:  "Generates a hierarchical map of the project structure, listing all local packages and their files, as well as a summary of external dependencies and standard library usage.",
		Instruction:  "*   **`project.map`**: Use this first when joining a new project to get a mental map.",
		Experimental: false,
	},
	"go.docs": {
		InternalName: "go.docs",
		ExternalName: "go.docs",
		Title:        "Go Documentation",
		Description:  "Retrieves documentation for a specific Go package. Lists exported types, functions, and variables. Supports returning output in Markdown or JSON format.",
		Instruction:  "*   **`go.docs`**: Efficiently lists sub-packages and exported symbols.",
		Experimental: false,
	},

	// --- GO TOOLCHAIN ---
	"go.build": {
		InternalName: "go.build",
		ExternalName: "go.build",
		Title:        "Go Build",
		Description:  "Executes the `go build` command for the specified packages or the current directory. Captures and returns the standard output and standard error to verify compilation status.",
		Instruction:  "*   **`go.build`**: Run this after a sequence of edits to ensure the whole project compiles.",
		Experimental: true,
	},
	"go.test": {
		InternalName: "go.test",
		ExternalName: "go.test",
		Title:        "Go Test",
		Description:  "Executes the `go test` command. Supports running tests for specific packages, filtering tests by regex (`-run`), and enabling verbose output or coverage analysis.",
		Instruction:  "*   **`go.test`**: Run specific tests to verify logic.",
		Experimental: true,
	},
	"go.install": {
		InternalName: "go.install",
		ExternalName: "go.install",
		Title:        "Go Install",
		Description:  "Executes the `go install` command to install packages or binaries to the environment.",
		Instruction:  "*   **`go.install`**: Use this to install packages.",
		Experimental: true,
	},
	"go.modernize": {
		InternalName: "go.modernize",
		ExternalName: "go.modernize",
		Title:        "Modernize Go Code",
		Description:  "Runs the `modernize` analyzer on the codebase to identify and optionally fix legacy Go patterns, replacing them with modern equivalents (e.g., `interface{}` to `any`).",
		Instruction:  "*   **`go.modernize`**: Run this to automatically upgrade old patterns (e.g. `interface{}` -> `any`, manual loops -> `slices`).",
		Experimental: true,
	},
	"go.diff": {
		InternalName: "go.diff",
		ExternalName: "go.diff",
		Title:        "Check API Diff",
		Description:  "Compares the public API of a Go package between two different versions using the `apidiff` tool. Reports incompatible changes to assess upgrade risks.",
		Instruction:  "*   **`go.diff`**: Run this BEFORE upgrading dependencies to catch breaking API changes (Risk Assessment).",
		Experimental: true,
	},

	// --- AGENTS ---
	"agent.review": {
		InternalName: "agent.review",
		ExternalName: "agent.review",
		Title:        "Code Review Agent",
		Description:  "Submit Go code to an AI reviewer. Returns a structured analysis focusing on correctness, idiomatic style, and potential bugs, with line-specific comments and severity levels.",
		Instruction:  "*   **`agent.review`**: Reviews Go code for correctness, style, and idiomatic usage.",
		Experimental: true,
	},
	"agent.specialist": {
		InternalName: "agent.specialist",
		ExternalName: "agent.specialist",
		Title:        "Specialist Agent",
		Description:  "Invokes a specialized autonomous agent capable of using investigation tools (read_docs, list_files, inspect_symbol) to answer complex queries about the codebase.",
		Instruction:  "*   **`agent.specialist`**: Use this if you are stuck or need access to more tools. DONT hallucinate tools, ask the specialist to provide them.",
		Experimental: false,
	},
	"agent.master": {
		InternalName: "agent.master",
		ExternalName: "agent.master",
		Title:        "Master Gopher",
		Description:  "Invokes the Master Gopher agent to analyze the user's request and dynamically update the list of available tools to best suit the current task.",
		Instruction:  "*   **`agent.master`**: Use this when you are unsure which tool to use or how to solve a problem. The Master will review your request, unlock appropriate capabilities in the server, and give you wise instructions.",
		Experimental: true,
	},
	
	// --- LEGACY/FALLBACK ---
	"file.edit_legacy": {
		InternalName: "file.edit_legacy",
		ExternalName: "file.edit_legacy",
		Title:        "Edit Code (Legacy)",
		Description:  "Modifies files using fuzzy matching context. (Legacy tool)",
		Instruction:  "*   **`file.edit_legacy`**: Modifies files using fuzzy matching context.",
		Experimental: false,
	},
}
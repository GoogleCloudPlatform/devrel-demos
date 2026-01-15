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
		Instruction:  "*   **`file.create`**: Create a new file from scratch.\n    *   **Usage:** `file.create(name=\"cmd/main.go\", content=\"package main\\n...\")`\n    *   **Outcome:** File is created, formatted, and imports are organized. Parent directories are created automatically.",
		Experimental: true,
	},
	"file.edit": {
		InternalName: "file.edit",
		ExternalName: "file.edit",
		Title:        "Edit File (Smart)",
		Description:  "Modifies an existing Go file using fuzzy matching or appending. If `search_context` is provided, locates the block with the highest similarity score and replaces it. If `search_context` is empty, appends content to the end. Automatically formats code using `goimports` and verifies syntax before saving.",
		Instruction:  "*   **`file.edit`**: Modify or append to an existing file.\n    *   **Modify:** `file.edit(file=\"main.go\", search_context=\"func old() {\\n}\", replacement=\"func new() {\\n}\")`\n    *   **Append:** `file.edit(file=\"main.go\", replacement=\"func newFunc() {\\n}\")` (Leave `search_context` empty)\n    *   **Outcome:** Code is patched, formatted, and syntax-checked. If the match fails, you will receive the best match found to help you correct the context.",
		Experimental: true,
	},
	"file.outline": {
		InternalName: "file.outline",
		ExternalName: "file.outline",
		Title:        "File Outline",
		Description:  "Parses a Go source file and returns a skeleton containing imports, type definitions, and function signatures. Does not include function bodies. Useful for quickly assessing file structure with minimal token usage.",
		Instruction:  "*   **`file.outline`**: Get the structure of a file without reading the entire body.\n    *   **Usage:** `file.outline(file=\"pkg/service.go\")`\n    *   **Outcome:** Returns imports, type definitions, and function signatures. Use this to quickly navigate large files.",
		Experimental: true,
	},
	"file.read": {
		InternalName: "file.read",
		ExternalName: "file.read",
		Title:        "Read File",
		Description:  "Reads and returns the complete content of a Go source file. Additionally extracts and lists a symbol table containing functions, types, and variables defined in the file.",
		Instruction:  "*   **`file.read`**: Read the full content of a file.\n    *   **Usage:** `file.read(file_path=\"pkg/utils.go\")`\n    *   **Outcome:** Returns the complete file content and a list of defined symbols (functions, types).",
		Experimental: false,
	},
	"file.list": {
		InternalName: "file.list",
		ExternalName: "file.list",
		Title:        "List Files",
		Description:  "Recursively lists files and directories starting from a specified root path. Supports depth limiting to manage output size.",
		Instruction:  "*   **`file.list`**: Explore the project structure.\n    *   **Usage:** `file.list(path=\".\", depth=2)`\n    *   **Outcome:** Lists files and directories up to the specified depth. Useful for discovering where code lives.",
		Experimental: true,
	},

	// --- SYMBOL OPERATIONS ---
	"symbol.inspect": {
		InternalName: "symbol.inspect",
		ExternalName: "symbol.inspect",
		Title:        "Inspect Symbol",
		Description:  "Retrieves detailed information for a specific Go symbol, including its signature, source code definition, and documentation comments. Resolves symbols using the project's knowledge graph.",
		Instruction:  "*   **`symbol.inspect`**: Get the definition and documentation of a specific symbol.\n    *   **Usage:** `symbol.inspect(package=\"fmt\", symbol=\"Println\")` or `symbol.inspect(file=\"main.go\", symbol=\"MyFunc\")`\n    *   **Outcome:** Returns the source code, documentation, and location of the symbol. Essential for understanding how to use or modify existing code.",
		Experimental: true,
	},
	"symbol.rename": {
		InternalName: "symbol.rename",
		ExternalName: "symbol.rename",
		Title:        "Rename Symbol",
		Description:  "Renames a Go identifier (function, type, variable) and updates all references throughout the codebase using the `gopls` tool to ensure semantic correctness.",
		Instruction:  "*   **`symbol.rename`**: Safely rename a symbol and update all references.\n    *   **Usage:** `symbol.rename(file=\"pkg/user.go\", line=10, col=5, new_name=\"Customer\")`\n    *   **Outcome:** The symbol is renamed globally, and all usages are updated. Prevents build errors caused by manual renaming.",
		Experimental: true,
	},

	// --- PROJECT & DOCS ---
	"project.map": {
		InternalName: "project.map",
		ExternalName: "project.map",
		Title:        "Project Map",
		Description:  "Generates a hierarchical map of the project structure, listing all local packages and their files, as well as a summary of external dependencies and standard library usage.",
		Instruction:  "*   **`project.map`**: Get a high-level overview of the project.\n    *   **Usage:** `project.map()`\n    *   **Outcome:** Returns a Markdown map of all packages, files, and dependencies. Use this when you first join a project to understand its layout.",
		Experimental: false,
	},
	"go.docs": {
		InternalName: "go.docs",
		ExternalName: "go.docs",
		Title:        "Go Documentation",
		Description:  "Retrieves documentation for a specific Go package. Lists exported types, functions, and variables. Supports returning output in Markdown or JSON format.",
		Instruction:  "*   **`go.docs`**: Read documentation for a package.\n    *   **Usage:** `go.docs(package_path=\"net/http\")`\n    *   **Outcome:** Returns a summary of exported symbols and package documentation. Use this to learn how to use a library.",
		Experimental: false,
	},

	// --- GO TOOLCHAIN ---
	"go.build": {
		InternalName: "go.build",
		ExternalName: "go.build",
		Title:        "Go Build",
		Description:  "Executes the `go build` command for the specified packages or the current directory. Captures and returns the standard output and standard error to verify compilation status.",
		Instruction:  "*   **`go.build`**: Compile the project to check for errors.\n    *   **Usage:** `go.build(packages=[\"./...\"])`\n    *   **Outcome:** Returns success or a list of compiler errors. Run this after making edits to ensure you haven't broken the build.",
		Experimental: true,
	},
	"go.test": {
		InternalName: "go.test",
		ExternalName: "go.test",
		Title:        "Go Test",
		Description:  "Executes the `go test` command. Supports running tests for specific packages, filtering tests by regex (`-run`), and enabling verbose output or coverage analysis.",
		Instruction:  "*   **`go.test`**: Run tests to verify logic.\n    *   **Usage:** `go.test(packages=[\"./pkg/...\"], run=\"TestAuth\")`\n    *   **Outcome:** Returns test results (PASS/FAIL). Use this to prevent regressions.",
		Experimental: true,
	},
	"go.install": {
		InternalName: "go.install",
		ExternalName: "go.install",
		Title:        "Go Install",
		Description:  "Executes the `go install` command to install packages or binaries to the environment.",
		Instruction:  "*   **`go.install`**: Install a Go tool or package.\n    *   **Usage:** `go.install(packages=[\"golang.org/x/tools/cmd/goimports@latest\"])`\n    *   **Outcome:** The package is installed to the environment.",
		Experimental: true,
	},
	"go.modernize": {
		InternalName: "go.modernize",
		ExternalName: "go.modernize",
		Title:        "Modernize Go Code",
		Description:  "Runs the `modernize` analyzer on the codebase to identify and optionally fix legacy Go patterns, replacing them with modern equivalents (e.g., `interface{}` to `any`).",
		Instruction:  "*   **`go.modernize`**: Automatically upgrade old Go patterns.\n    *   **Usage:** `go.modernize(dir=\".\", fix=true)`\n    *   **Outcome:** Replaces legacy code (e.g., `interface{}`) with modern equivalents (e.g., `any`).",
		Experimental: true,
	},
	"go.diff": {
		InternalName: "go.diff",
		ExternalName: "go.diff",
		Title:        "Check API Diff",
		Description:  "Compares the public API of a Go package between two different versions using the `apidiff` tool. Reports incompatible changes to assess upgrade risks.",
		Instruction:  "*   **`go.diff`**: Check for breaking API changes.\n    *   **Usage:** `go.diff(old=\"v1.0.0\", new=\".\")`\n    *   **Outcome:** Reports incompatible changes in the public API. Use this before upgrading dependencies.",
		Experimental: true,
	},

	// --- AGENTS ---
	"agent.review": {
		InternalName: "agent.review",
		ExternalName: "agent.review",
		Title:        "Code Review Agent",
		Description:  "Submit Go code to an AI reviewer. Returns a structured analysis focusing on correctness, idiomatic style, and potential bugs, with line-specific comments and severity levels.",
		Instruction:  "*   **`agent.review`**: Request an expert code review.\n    *   **Usage:** `agent.review(file_content=\"...\")`\n    *   **Outcome:** Returns a list of suggestions, bugs, and style improvements.",
		Experimental: true,
	},
	"agent.specialist": {
		InternalName: "agent.specialist",
		ExternalName: "agent.specialist",
		Title:        "Specialist Agent",
		Description:  "Invokes a specialized autonomous agent capable of using investigation tools (read_docs, list_files, inspect_symbol) to answer complex queries about the codebase.",
		Instruction:  "*   **`agent.specialist`**: Ask a complex question that requires investigation.\n    *   **Usage:** `agent.specialist(query=\"How does the authentication middleware work?\")`\n    *   **Outcome:** The Specialist investigates the code and provides a detailed answer.",
		Experimental: false,
	},
	"agent.master": {
		InternalName: "agent.master",
		ExternalName: "agent.master",
		Title:        "Master Gopher",
		Description:  "Invokes the Master Gopher agent to analyze the user's request and dynamically update the list of available tools to best suit the current task.",
		Instruction:  "*   **`agent.master`**: Get help deciding which tools to use.\n    *   **Usage:** `agent.master(query=\"I need to refactor the user service.\")`\n    *   **Outcome:** The Master Gopher selects and enables the best tools for your task.",
		Experimental: true,
	},
}

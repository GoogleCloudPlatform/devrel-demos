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

// Registry holds all tool definitions, keyed by InternalName.
var Registry = map[string]ToolDef{
	// --- FILE OPERATIONS ---
	"file.create": {
		InternalName: "file.create",
		ExternalName: "file.create",
		Title:        "Initialize File",
		Description:  "Create a new source file from scratch. Automatically handles directory creation, package boilerplate, and import organization.",
		Instruction:  "*   **`file.create`**: Initialize a new file. Essential for adding new modules or entry points.\n    *   **Usage:** `file.create(name=\"cmd/main.go\", content=\"package main\\n...\")`\n    *   **Outcome:** File is created and formatted to standard.",
		Experimental: true,
	},
	"file.edit": {
		InternalName: "file.edit",
		ExternalName: "file.edit",
		Title:        "Patch File",
		Description:  "Perform a targeted code modification. Uses fuzzy-matching to locate and patch specific logic blocks, or appends new code if no context is provided. Always verifies syntax integrity before saving.",
		Instruction:  "*   **`file.edit`**: Modify or extend existing logic. The primary tool for bug fixes and refactoring.\n    *   **Modify:** `file.edit(file=\"main.go\", search_context=\"func old() {\\n}\", replacement=\"func new() {\\n}\")`\n    *   **Append:** `file.edit(file=\"main.go\", replacement=\"func newFunc() {\\n}\")` (Leave `search_context` empty)\n    *   **Outcome:** Code is updated and pre-verified for build safety.",
		Experimental: true,
	},
	"file.outline": {
		InternalName: "file.outline",
		ExternalName: "file.outline",
		Title:        "Scan Structure",
		Description:  "Examine the structural layout of a file. Returns imports, types, and function signatures. Use this to orient yourself without consuming large amounts of context.",
		Instruction:  "*   **`file.outline`**: Perform a quick structural scan. Perfect for assessing a file's responsibilities.\n    *   **Usage:** `file.outline(file=\"pkg/service.go\")`\n    *   **Outcome:** Lightweight structural map of the file.",
		Experimental: true,
	},
	"file.read": {
		InternalName: "file.read",
		ExternalName: "file.read",
		Title:        "Examine Content",
		Description:  "Perform a deep read of a file. Returns the full source code and a detailed symbol table of all declarations. Use this when implementation details are required.",
		Instruction:  "*   **`file.read`**: Deep-dive into a file's implementation.\n    *   **Usage:** `file.read(file_path=\"pkg/utils.go\")`\n    *   **Outcome:** Complete implementation source and symbol index.",
		Experimental: false,
	},
	"file.list": {
		InternalName: "file.list",
		ExternalName: "file.list",
		Title:        "Survey Directory",
		Description:  "Explore the project hierarchy recursively. Use this to locate modules, understand the architecture, and find relevant source files.",
		Instruction:  "*   **`file.list`**: Map the project territory.\n    *   **Usage:** `file.list(path=\".\", depth=2)`\n    *   **Outcome:** Hierarchical list of files and directories.",
		Experimental: true,
	},

	// --- SYMBOL OPERATIONS ---
	"symbol.inspect": {
		InternalName: "symbol.inspect",
		ExternalName: "symbol.inspect",
		Title:        "Diagnose Symbol",
		Description:  "Perform a deep-dive analysis of a specific symbol. Resolves its exact definition, documentation, and references using the project knowledge graph. Essential for assessing usage and impact.",
		Instruction:  "*   **`symbol.inspect`**: Get the ground truth for a symbol.\n    *   **Usage:** `symbol.inspect(package=\"fmt\", symbol=\"Println\")` or `symbol.inspect(file=\"main.go\", symbol=\"MyFunc\")`\n    *   **Outcome:** Source definition and comprehensive metadata for the symbol.",
		Experimental: true,
	},
	"symbol.rename": {
		InternalName: "symbol.rename",
		ExternalName: "symbol.rename",
		Title:        "Refactor Symbol",
		Description:  "Execute a safe, semantic rename of a Go identifier. Updates all call sites and references throughout the codebase to maintain structural integrity.",
		Instruction:  "*   **`symbol.rename`**: Safely update a symbol's identity across the entire project.\n    *   **Usage:** `symbol.rename(file=\"pkg/user.go\", line=10, col=5, new_name=\"Customer\")`\n    *   **Outcome:** Semantic renaming with zero broken references.",
		Experimental: true,
	},

	// --- PROJECT & DOCS ---
	"project.map": {
		InternalName: "project.map",
		ExternalName: "project.map",
		Title:        "Assess Architecture",
		Description:  "Generates a hierarchical map of the project structure, listing all local packages and their files, as well as a summary of external dependencies.",
		Instruction:  "*   **`project.map`**: Get the high-level project structure.\n    *   **Usage:** `project.map()`\n    *   **Outcome:** A complete architectural map of the repository files and packages.",
		Experimental: false,
	},
	"go.docs": {
		InternalName: "go.docs",
		ExternalName: "go.docs",
		Title:        "Consult Docs",
		Description:  "Query Go documentation for any package or symbol in the ecosystem. Supports standard library and third-party modules. Essential for learning API usage.",
		Instruction:  "*   **`go.docs`**: Consult the documentation library.\n    *   **Usage:** `go.docs(package_path=\"net/http\")`\n    *   **Outcome:** API reference and usage guidance.",
		Experimental: false,
	},

	// --- GO TOOLCHAIN ---
	"go.build": {
		InternalName: "go.build",
		ExternalName: "go.build",
		Title:        "Go Build",
		Description:  "Compiles the packages named by the import paths, along with their dependencies. Generates an executable binary if `main` package is targeted.",
		Instruction:  "*   **`go.build`**: Compile the project to check for errors.\n    *   **Usage:** `go.build(packages=[\"./...\"])`\n    *   **Outcome:** Build status report (Success or Error Log).",
		Experimental: true,
	},
	"go.test": {
		InternalName: "go.test",
		ExternalName: "go.test",
		Title:        "Run Tests",
		Description:  "Execute the test suite to verify logical correctness. Supports package-level testing and regex filtering for specific test cases.",
		Instruction:  "*   **`go.test`**: Verify logic and prevent regressions.\n    *   **Usage:** `go.test(packages=[\"./pkg/...\"], run=\"TestAuth\")`\n    *   **Outcome:** Test execution report (PASS/FAIL).",
		Experimental: true,
	},
	"go.install": {
		InternalName: "go.install",
		ExternalName: "go.install",
		Title:        "Go Install",
		Description:  "Compiles and installs the package/binary to `$GOPATH/bin`. Use this to install tools or the current project.",
		Instruction:  "*   **`go.install`**: Add new tools or dependencies.\n    *   **Usage:** `go.install(packages=[\"golang.org/x/tools/cmd/goimports@latest\"])`\n    *   **Outcome:** Successful installation of the target package.",
		Experimental: true,
	},
	"go.get": {
		InternalName: "go.get",
		ExternalName: "go.get",
		Title:        "Go Get",
		Description:  "Downloads and installs the packages named by the import paths, along with their dependencies. Updates `go.mod`.",
		Instruction:  "*   **`go.get`**: Add a new dependency to the module.\n    *   **Usage:** `go.get(packages=[\"github.com/gin-gonic/gin@latest\"])`\n    *   **Outcome:** Module added to go.mod and downloaded.",
		Experimental: true,
	},
	"go.mod": {
		InternalName: "go.mod",
		ExternalName: "go.mod",
		Title:        "Go Mod",
		Description:  "Provides access to module maintenance operations like `go mod tidy`.",
		Instruction:  "*   **`go.mod`**: Manage module requirements.\n    *   **Usage:** `go.mod(command=\"tidy\")`\n    *   **Outcome:** go.mod and go.sum are updated/cleaned.",
		Experimental: true,
	},
	"go.lint": {
		InternalName: "go.lint",
		ExternalName: "go.lint",
		Title:        "Go Lint",
		Description:  "Runs 'golangci-lint' on the project. Automatically installs the linter if it is not found in the path.",
		Instruction:  "*   **`go.lint`**: Analyze code quality.\n    *   **Usage:** `go.lint(args=[\"./...\"])`\n    *   **Outcome:** A report of style and correctness issues.",
		Experimental: true,
	},
	"go.modernize": {
		InternalName: "go.modernize",
		ExternalName: "go.modernize",
		Title:        "Modernize Code",
		Description:  "Analyze and automatically upgrade legacy Go patterns to modern standards. Replaces outdated constructs with performant, modern equivalents.",
		Instruction:  "*   **`go.modernize`**: Proactively upgrade legacy patterns.\n    *   **Usage:** `go.modernize(dir=\".\", fix=true)`\n    *   **Outcome:** Clean, modern Go source code.",
		Experimental: true,
	},
	"go.diff": {
		InternalName: "go.diff",
		ExternalName: "go.diff",
		Title:        "Assess API Risk",
		Description:  "Compare the public API of two versions of a package. Detects breaking changes and incompatible updates using `apidiff`.",
		Instruction:  "*   **`go.diff`**: Perform a risk assessment for updates.\n    *   **Usage:** `go.diff(old=\"v1.0.0\", new=\".\")`\n    *   **Outcome:** Report on incompatible API changes.",
		Experimental: true,
	},

	// --- AGENTS ---
	"agent.review": {
		InternalName: "agent.review",
		ExternalName: "agent.review",
		Title:        "Request Review",
		Description:  "Submit code for expert analysis. Returns a structured critique focusing on correctness, idiomatic style, and potential edge cases.",
		Instruction:  "*   **`agent.review`**: Get an expert peer review.\n    *   **Usage:** `agent.review(file_content=\"...\")`\n    *   **Outcome:** Actionable suggestions and bug findings.",
		Experimental: true,
	},
	"agent.specialist": {
		InternalName: "agent.specialist",
		ExternalName: "agent.specialist",
		Title:        "Consult Specialist",
		Description:  "Delegate complex investigation to a specialized autonomous agent. The specialist can independently research the codebase to answer difficult architectural questions.",
		Instruction:  "*   **`agent.specialist`**: Ask a question requiring deep research.\n    *   **Usage:** `agent.specialist(query=\"How does the auth flow handle token expiry?\")`\n    *   **Outcome:** Comprehensive investigative report.",
		Experimental: false,
	},
}

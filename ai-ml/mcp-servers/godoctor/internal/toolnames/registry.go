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
		Title:       "Initialize File",
		Description: "Create a new source file from scratch. Automatically handles directory creation, package boilerplate, and import organization.",
		Instruction: "*   **`file_create`**: Initialize a new file. Essential for adding new modules or entry points.\n    *   **Usage:** `file_create(filename=\"cmd/main.go\", content=\"package main\\n...\")`\n    *   **Outcome:** File is created and formatted to standard.",
	},
	"file_edit": {
		Name:        "file_edit",
		Title:       "Patch File",
		Description: "Perform a targeted code modification. Uses fuzzy-matching to locate and patch specific logic blocks. For Go files, it auto-formats and verifies compilation before finalizing.",
		Instruction: "*   **`file_edit`**: Modify or extend existing logic. The primary tool for bug fixes and refactoring.\n    *   **Modify:** `file_edit(filename=\"main.go\", search_context=\"func old() {\\n}\", replacement=\"func new() {\\n}\")`\n    *   **Append:** `file_edit(filename=\"main.go\", replacement=\"func newFunc() {\\n}\")` (Leave `search_context` empty)\n    *   **Note:** Ensure `search_context` is unique and matches the target distinctively.\n    *   **Outcome:** Code is updated. Go code is verified for compilation errors.",
	},
	"file_outline": {
		Name:        "file_outline",
		Title:       "Scan Structure",
		Description: "Examine the structural layout of a file. Returns imports, types, and function signatures. Use this to orient yourself without consuming large amounts of context.",
		Instruction: "*   **`file_outline`**: Perform a quick structural scan. Perfect for assessing a file's responsibilities.\n    *   **Usage:** `file_outline(filename=\"pkg/service.go\")`\n    *   **Outcome:** Lightweight structural map of the file.",
	},
	"file_read": {
		Name:        "file_read",
		Title:       "Examine Content",
		Description: "Read file content with added context. Returns source code and a list of referenced external symbols with their signatures and documentation (similar to IDE hover).",
		Instruction: "*   **`file_read`**: Read file content with context. Supports partial reading.\n    *   **Usage:** `file_read(filename=\"pkg/utils.go\")` or `file_read(filename=\"pkg/utils.go\", start_line=10, end_line=50)`\n    *   **Outcome:** Source code and external symbol context (signatures/docs).",
	},
	"file_list": {
		Name:        "file_list",
		Title:       "Survey Directory",
		Description: "Explore the project hierarchy recursively. Use this to locate modules, understand the architecture, and find relevant source files.",
		Instruction: "*   **`file_list`**: Map the project territory.\n    *   **Usage:** `file_list(path=\".\", depth=2)`\n    *   **Outcome:** Hierarchical list of files and directories.",
	},
	// --- SHELL OPERATIONS ---
	"safe_shell": {
		Name:        "safe_shell",
		Title:       "Safe Execution",
		Description: "Execute a specific binary with arguments. Supports long-running tasks up to 5 minutes. Output is capped.",
		Instruction: "*   **`safe_shell`**: Run a CLI command safely. Output is capped. Supports long-running tasks up to 5 minutes.\n    *   **Usage:** `safe_shell(command=\"go\", args=[\"test\", \"./...\"], timeout_seconds=300)`\n    *   **Note:** Use `args` for command arguments (e.g., `echo \"hello\"` -> `args: [\"hello\"]`). Use `stdin` ONLY for piping input to commands that read from stdin (e.g., `cat`).\n    *   **Outcome:** Command stdout/stderr (truncated if large).",
	},

	// --- SYMBOL OPERATIONS ---
	"symbol_inspect": {
		Name:        "symbol_inspect",
		Title:       "Diagnose Symbol",
		Description: "Perform a deep-dive analysis of a specific symbol. Resolves its exact definition, documentation, and references using the project knowledge graph. Essential for assessing usage and impact.",
		Instruction: "*   **`symbol_inspect`**: Get the ground truth for a symbol.\n    *   **Usage:** `symbol_inspect(import_path=\"fmt\", symbol_name=\"Println\")` or `symbol_inspect(filename=\"main.go\", symbol_name=\"MyFunc\")`\n    *   **Outcome:** Source definition and comprehensive metadata for the symbol.",
	},
	"symbol_rename": {
		Name:        "symbol_rename",
		Title:       "Refactor Symbol",
		Description: "Execute a safe, semantic rename of a Go identifier. Updates all call sites and references throughout the codebase to maintain structural integrity.",
		Instruction: "*   **`symbol_rename`**: Safely update a symbol's identity across the entire project.\n    *   **Usage:** `symbol_rename(filename=\"pkg/user.go\", line=10, column=5, new_name=\"Customer\")`\n    *   **Outcome:** Semantic renaming preserving structural integrity.",
	},

	// --- DOCS ---
	"go_docs": {
		Name:        "go_docs",
		Title:       "Consult Docs",
		Description: "Query Go documentation for any package or symbol in the ecosystem. Supports standard library and third-party modules. Essential for learning API usage.",
		Instruction: "*   **`go_docs`**: Consult the documentation library.\n    *   **Usage:** `go_docs(import_path=\"net/http\")`\n    *   **Outcome:** API reference and usage guidance.",
	},

	// --- GO TOOLCHAIN ---
	"go_build": {
		Name:        "go_build",
		Title:       "Go Build",
		Description: "Compiles the packages named by the import paths, along with their dependencies. Generates an executable binary if `main` package is targeted.",
		Instruction: "*   **`go_build`**: Compile the project to check for errors.\n    *   **Usage:** `go_build(packages=[\"./...\"])`\n    *   **Outcome:** Build status report (Success or Error Log).",
	},
	"go_test": {
		Name:        "go_test",
		Title:       "Run Tests",
		Description: "Execute the test suite to verify logical correctness. Supports package-level testing and regex filtering for specific test cases.",
		Instruction: "*   **`go_test`**: Verify logic and prevent regressions.\n    *   **Usage:** `go_test(packages=[\"./pkg/...\"], run=\"TestAuth\")`\n    *   **Outcome:** Test execution report (PASS/FAIL).",
	},
	"go_get": {
		Name:        "go_get",
		Title:       "Go Get",
		Description: "Downloads and installs the packages named by the import paths, along with their dependencies. Updates `go.mod`.",
		Instruction: "*   **`go_get`**: Add a new dependency to the module.\n    *   **Usage:** `go_get(packages=[\"github.com/gin-gonic/gin@latest\"])`\n    *   **Outcome:** Module added to go.mod and downloaded.",
	},
	"go_modernize": {
		Name:        "go_modernize",
		Title:       "Modernize Code",
		Description: "Analyze and automatically upgrade legacy Go patterns to modern standards. Replaces outdated constructs with performant, modern equivalents.",
		Instruction: "*   **`go_modernize`**: Proactively upgrade legacy patterns.\n    *   **Usage:** `go_modernize(dir=\".\", fix=true)`\n    *   **Outcome:** Clean, modern Go source code.",
	},
	"go_diff": {
		Name:        "go_diff",
		Title:       "Assess API Risk",
		Description: "Compare the public API of two versions of a package. Detects breaking changes and incompatible updates using `apidiff`.",
		Instruction: "*   **`go_diff`**: Perform a risk assessment for updates.\n    *   **Usage:** `go_diff(old=\"v1.0.0\", new=\".\")`\n    *   **Outcome:** Report on incompatible API changes.",
	},

	// --- AGENTS ---
	"code_review": {
		Name:        "code_review",
		Title:       "Request Review",
		Description: "Submit code for expert analysis. Returns a structured Markdown report focusing on correctness, idiomatic style, and potential edge cases.",
		Instruction: "*   **`code_review`**: Get an expert peer review.\n    *   **Usage:** `code_review(file_content=\"...\")`\n    *   **Outcome:** Markdown report with actionable suggestions and bug findings.",
	},
}

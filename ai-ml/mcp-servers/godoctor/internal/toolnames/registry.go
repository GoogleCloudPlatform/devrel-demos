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
		Title:       "Initialize File",
		Description: "Create a new source file from scratch. Automatically handles directory creation, package boilerplate, and import organization.",
		Instruction: "*   **`file_create`**: Initialize a new file. Essential for adding new modules or entry points.\n    *   **Usage:** `file_create(filename=\"cmd/main.go\", content=\"package main\n...\")`\n    *   **Outcome:** File is created and formatted to standard.",
	},
	"smart_edit": {
		Name:        "smart_edit",
		Title:       "Patch File",
		Description: "Perform a targeted code modification. Uses Levenshtein distance to locate and patch specific logic blocks. For Go files, it auto-formats and verifies compilation before finalizing.",
		Instruction: "*   **`smart_edit`**: The primary tool for code modification. Uses Levenshtein distance for robust matching.\n    *   **Modify:** `smart_edit(filename=\"main.go\", old_content=\"func old() {\n}\", new_content=\"func new() {\n}\")`. Ensure `old_content` is unique (3-4 lines).\n    *   **Append:** `smart_edit(filename=\"main.go\", new_content=\"func newFunc() {\n}\")` (Leave `old_content` empty to append to file).\n    *   **Line Isolation (RECOMMENDED):** Use `start_line`/`end_line` to disambiguate matches and prevent accidental changes to wrong locations.\n    *   **Error Recovery:** If an edit produces invalid Go code, the tool returns the specific syntax error along with a **context snippet** showing the lines around the failure to help you debug the replacement.\n    *   **Outcome:** Code is updated, formatted (gofmt), and verified.",
	},
	"smart_read": {
		Name:        "smart_read",
		Title:       "Inspect Code",
		Description: "Read file content or structure. Returns source code (full or snippet) or AST outline (signatures only). Consolidates reading and outlining.",
		Instruction: "*   **`smart_read`**: The universal reader. Inspect code or structure.\n    *   **Read All:** `smart_read(filename=\"pkg/utils.go\")`\n    *   **Outline:** `smart_read(filename=\"pkg/utils.go\", outline=true)` (Use for large files to see structure without bodies).\n    *   **Snippet:** `smart_read(filename=\"pkg/utils.go\", start_line=10, end_line=50)` (Targeted read).\n    *   **Outcome:** Source code or AST outline.",
	},
	"list_files": {
		Name:        "list_files",
		Title:       "Survey Directory",
		Description: "Explore the project hierarchy recursively. Use this to locate modules, understand the architecture, and find relevant source files. Note: Uses built-in heuristics to ignore common artifact directories; does not yet fully parse .gitignore.",
		Instruction: "*   **`list_files`**: Map the project territory.\n    *   **Usage:** `list_files(path=\".\", depth=2)`\n    *   **Outcome:** Hierarchical list of files and directories.",
	},

	// --- DOCS ---
	"read_docs": {
		Name:        "read_docs",
		Title:       "Consult Docs",
		Description: "Query Go documentation for any package or symbol in the ecosystem. Supports standard library and third-party modules. Essential for learning API usage.",
		Instruction: "*   **`read_docs`**: Consult the documentation library.\n    *   **Usage:** `read_docs(import_path=\"net/http\")`\n    *   **Outcome:** API reference and usage guidance.",
	},

	// --- GO TOOLCHAIN ---
	"verify_build": {
		Name:        "verify_build",
		Title:       "Verify Build",
		Description: "Compiles the packages named by the import paths, along with their dependencies. Generates an executable binary if `main` package is targeted.",
		Instruction: "*   **`verify_build`**: Compile the project to check for errors.\n    *   **Usage:** `verify_build(packages=[\"./...\"])`\n    *   **Outcome:** Build status report (Success or Error Log).",
	},
	"verify_tests": {
		Name:        "verify_tests",
		Title:       "Verify Tests",
		Description: "Execute the test suite to verify logical correctness. Supports package-level testing and regex filtering for specific test cases.",
		Instruction: "*   **`verify_tests`**: Verify logic and prevent regressions.\n    *   **Usage:** `verify_tests(packages=[\"./pkg/...\"], run=\"TestAuth\")`\n    *   **Outcome:** Test execution report (PASS/FAIL).",
	},
	"add_dependency": {
		Name:        "add_dependency",
		Title:       "Add Dependency",
		Description: "Downloads and installs the packages named by the import paths, along with their dependencies. Updates `go.mod`.",
		Instruction: "*   **`add_dependency`**: Add a new dependency and fetch its docs.\n    *   **Usage:** `add_dependency(packages=[\"github.com/gin-gonic/gin@latest\"])`\n    *   **Outcome:** Module added, downloaded, and **documentation returned**.",
	},
	"modernize_code": {
		Name:        "modernize_code",
		Title:       "Modernize Code",
		Description: "Analyze and automatically upgrade legacy Go patterns to modern standards. Replaces outdated constructs with performant, modern equivalents.",
		Instruction: "*   **`modernize_code`**: Proactively upgrade legacy patterns.\n    *   **Usage:** `modernize_code(dir=\".\", fix=true)`\n    *   **Outcome:** Clean, modern Go source code.",
	},
	"check_api": {
		Name:        "check_api",
		Title:       "Assess API Risk",
		Description: "Compare the public API of two versions of a package. Detects breaking changes using `apidiff`. **Requires `apidiff` installed and available in the PATH.**",
		Instruction: "*   **`check_api`**: Perform a risk assessment for updates.\n    *   **Usage:** `check_api(old=\"v1.0.0\", new=\".\")`\n    *   **Outcome:** Report on incompatible API changes.",
	},

	// --- AGENTS ---
	"code_review": {
		Name:        "code_review",
		Title:       "Code Review",
		Description: "Submit code for expert analysis. Returns a structured Markdown report. **Requires `GOOGLE_API_KEY` (Gemini) or Google Cloud Vertex AI configuration.**",
		Instruction: "*   **`code_review`**: Get an expert peer review.\n    *   **Usage:** `code_review(file_content=\"...\")`\n    *   **Outcome:** Markdown report with actionable suggestions and bug findings.",
	},
}

package instructions

// Get returns the agent instructions for the server.
func Get(experimental bool) string {
	if experimental {
		return experimentalInstructions
	}
	return stableInstructions
}

const experimentalInstructions = `# Go Development Toolkit

This server provides a set of tools for expert Go software engineering.

## Core Workflow (Context-Aware)

Use these tools for the most robust and "compiler-verified" experience. They maintain a Knowledge Graph of the project to ensure safety.

### 1. open
**Purpose:** The entry point for exploring code.
**Description:** Loads a file into the context and returns a **Skeleton View** (package, imports, types, function signatures).
**Usage:** Call this first to understand a file's structure without being overwhelmed by implementation details.
**Parameters:**
- ` + "`" + `file` + "`" + ` (string, required): The path to the .go file.

### 2. describe
**Purpose:** The deep-dive explorer.
**Description:** Retrieves full documentation, implementation source code, and usage references for any symbol.
**Usage:** Use this after ` + "`" + `open` + "`" + ` to read the body of a specific function or understand an external package.
**Parameters:**
- ` + "`" + `symbol` + "`" + ` (string, optional): The name of the function, type, or var (e.g., "User", "http.Client").
- ` + "`" + `package` + "`" + ` (string, optional): The import path (e.g., "fmt").
- ` + "`" + `file` + "`" + ` (string, optional): A local file path context.

### 3. edit
**Purpose:** The safe code modifier.
**Description:** Edits code with whitespace-agnostic fuzzy matching. It runs post-edit verification to warn about compilation errors or broken references.
**Parameters:**
- ` + "`" + `file` + "`" + ` (string, required): The file to edit.
- ` + "`" + `search_context` + "`" + ` (string, required): The block of code to find (ignores whitespace).
- ` + "`" + `replacement` + "`" + ` (string, required): The new code.
- ` + "`" + `autofix` + "`" + ` (int, optional): Similarity threshold (default 95).

### 4. write
**Purpose:** Creator and appender.
**Description:** Creates new files or appends content to existing ones, with automatic import validation.
**Parameters:**
- ` + "`" + `name` + "`" + ` (string, required): File path.
- ` + "`" + `content` + "`" + ` (string, required): The content to write.
- ` + "`" + `mode` + "`" + ` (string, optional): "append" (default) or "overwrite".

---

## Standard Tools (Legacy/Stable)

These tools are always available.

### 5. read_code
**Description:** Reads a file and returns its full content plus a symbol table. Useful for quick, stateless reads.

### 6. read_docs
**Description:** Fetches documentation for packages. (Superseded by ` + "`" + `describe` + "`" + ` in experimental mode).

### 7. edit_code
**Description:** Standard fuzzy-matching editor. (Superseded by ` + "`" + `edit` + "`" + ` in experimental mode).

### 8. review_code
**Description:** AI-powered code review. Returns structured feedback on style and correctness.

## Recommended Workflow

1.  **Start:** ` + "`" + `open("main.go")` + "`" + ` -> Get the skeleton.
2.  **Explore:** ` + "`" + `describe(symbol="User")` + "`" + ` -> See the struct definition and methods.
3.  **Plan:** Check usages in the output of ` + "`" + `describe` + "`" + `.
4.  **Act:** ` + "`" + `edit(...)` + "`" + ` or ` + "`" + `write(...)` + "`" + `.
5.  **Verify:** Check the output of ` + "`" + `edit` + "`" + ` for any "Impact Warnings".`

const stableInstructions = `# Go Development Toolkit

Use the following tool definitions to enable expert Go software engineering capabilities.

## Tool Definitions

### 1. review_code
**Description:** Analyze Go code for correctness, style, and idiomatic usage.
**Parameters:**
- ` + "`" + `file_content` + "`" + ` (string, required): The content of the Go file to review.
- ` + "`" + `model_name` + "`" + ` (string, optional): The Gemini model to use (default: gemini-2.5-pro).
- ` + "`" + `hint` + "`" + ` (string, optional): A specific focus for the review (e.g., "check for concurrency bugs").

### 2. read_docs
**Description:** Retrieve Go documentation for packages and symbols.
**Parameters:**
- ` + "`" + `package_path` + "`" + ` (string, required): The import path of the package (e.g., "fmt", "net/http").
- ` + "`" + `symbol_name` + "`" + ` (string, optional): The name of the function, type, or variable to look up.

### 3. read_code
**Description:** Read a Go file and extract a structured symbol table.
**Parameters:**
- ` + "`" + `file_path` + "`" + ` (string, required): The path to the file to read.

### 4. edit_code
**Description:** Smart file editing tool with fuzzy matching and auto-formatting.
**Parameters:**
- ` + "`" + `file_path` + "`" + ` (string, required): The path to the file to modify.
- ` + "`" + `search_context` + "`" + ` (string, optional): The exact code block to replace. Required for "replace_block" and "replace_all" strategies.
- ` + "`" + `new_content` + "`" + ` (string, required): The new code to insert.
- ` + "`" + `strategy` + "`" + ` (string, optional): "replace_block" (default), "replace_all", "overwrite_file", or "append".
- ` + "`" + `autofix` + "`" + ` (boolean, optional): If true, attempts to fix minor typos in search_context.

## Usage Guidelines

1.  **Exploration:** Start by using ` + "`" + `read_code` + "`" + ` to understand the file structure and ` + "`" + `read_docs` + "`" + ` to learn about unknown packages.
2.  **Review:** Use ` + "`" + `review_code` + "`" + ` to check for potential issues before making changes.
3.  **Editing:** Use ` + "`" + `edit_code` + "`" + ` to safely modify files. Always verify the output.`
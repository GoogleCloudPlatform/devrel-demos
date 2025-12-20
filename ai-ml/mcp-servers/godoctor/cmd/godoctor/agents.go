package main

import (
	"fmt"
)

func printAgentInstructions() {
	fmt.Println(`# Go Development Toolkit

Use the following tool definitions to enable expert Go software engineering capabilities.

## Tool Definitions

### 1. review_code
**Description:** Analyze Go code for correctness, style, and idiomatic usage.
**Parameters:**
- ` + "`" + `file_content` + "`" + ` (string, required): The content of the Go file to review.
- ` + "`" + `model_name` + "`" + ` (string, optional): The Gemini model to use (default: gemini-2.5-pro).
- ` + "`" + `hint` + "`" + ` (string, optional): A specific focus for the review (e.g., "check for concurrency bugs").

### 2. read_godoc
**Description:** Retrieve Go documentation for packages and symbols.
**Parameters:**
- ` + "`" + `package_path` + "`" + ` (string, required): The import path of the package (e.g., "fmt", "net/http").
- ` + "`" + `symbol_name` + "`" + ` (string, optional): The name of the function, type, or variable to look up.

### 3. inspect_file
**Description:** Analyze a Go file to understand its dependencies and external symbol usage.
**Parameters:**
- ` + "`" + `file_path` + "`" + ` (string, required): The path to the file to inspect.

### 4. edit_code
**Description:** Smart file editing tool with fuzzy matching and auto-formatting.
**Parameters:**
- ` + "`" + `file_path` + "`" + ` (string, required): The path to the file to modify.
- ` + "`" + `search_context` + "`" + ` (string, optional): The exact code block to replace. Required for "single_match" and "replace_all" strategies.
- ` + "`" + `new_content` + "`" + ` (string, required): The new code to insert.
- ` + "`" + `strategy` + "`" + ` (string, optional): "single_match" (default), "replace_all", or "overwrite_file".
- ` + "`" + `autofix` + "`" + ` (boolean, optional): If true, attempts to fix minor typos in search_context.

## Usage Guidelines

1.  **Exploration:** Start by using ` + "`" + `inspect_file` + "`" + ` to understand the file structure and ` + "`" + `read_godoc` + "`" + ` to learn about unknown packages.
2.  **Review:** Use ` + "`" + `review_code` + "`" + ` to check for potential issues before making changes.
3.  **Editing:** Use ` + "`" + `edit_code` + "`" + ` to safely modify files. Always verify the output.
`)
}

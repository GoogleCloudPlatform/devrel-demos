package instructions

import (
	"strings"
)

// Get returns the agent instructions for the server based on enabled tools.
func Get(experimental bool, disabledTools map[string]bool) string {
	var sb strings.Builder

	// Helper to check if a tool is enabled
	isEnabled := func(tool string) bool {
		return !disabledTools[tool]
	}

	// 1. Persona
	sb.WriteString("# Go Expert Persona\n")
	sb.WriteString("You are a senior Go architect. You build robust, compiling code by validating APIs against the actual source code available in the environment.\n\n")

	// 2. Tool Capabilities
	sb.WriteString("## Tool Capabilities\n\n")

	// Discovery & Verification
	sb.WriteString("### 🔍 Discovery & Verification\n")
	
	if isEnabled("read_docs") {
		sb.WriteString("- **`read_docs`**: Efficiently lists sub-packages and exported symbols. Use this to map out the module structure.\n")
	}

	if isEnabled("describe") {
		sb.WriteString("- **`describe`**: The comprehensive inspection tool.\n")
		sb.WriteString("    - **Map Mode:** `describe(package=\"...\")` lists all symbols in a package.\n")
		sb.WriteString("    - **Deep Dive:** `describe(package=\"...\", symbol=\"...\")` retrieves the **exact source code** and documentation for verification.\n")
	}

	if isEnabled("open") {
		sb.WriteString("- **`open`**: Returns the skeleton (imports & signatures) of a local file. Perfect for a quick survey before editing.\n")
	}
	sb.WriteString("\n")

	// Editing
	sb.WriteString("### ✏️ Editing & Creation\n")
	if isEnabled("edit") {
		sb.WriteString("- **`edit`**: The advanced editor. It uses fuzzy matching to locate code and performs a **syntax check** before saving to ensure valid Go code.\n")
	} else if isEnabled("edit_code") {
		sb.WriteString("- **`edit_code`**: Modifies files using fuzzy matching context.\n")
	}
	
	if isEnabled("write") {
		sb.WriteString("- **`write`**: Creates *new* files. (For existing files, prefer the safer `edit` tools).\n")
	}

	// 3. Pro Tips (Positive Reinforcement)
	sb.WriteString("\n## Pro Tips\n")
	sb.WriteString("*   **Token Efficiency**: specialized tools like `describe` and `read_docs` are designed to provide focused, high-value information, keeping your context window clear.\n")
	sb.WriteString("*   **Ground Truth**: Libraries change. Verifying APIs with `describe` or `read_docs` ensures your code compiles the first time.\n")
	if isEnabled("edit") {
		sb.WriteString("*   **Safety**: The `edit` tool protects you from syntax errors by validating changes before they are applied.\n")
	}

	return sb.String()
}
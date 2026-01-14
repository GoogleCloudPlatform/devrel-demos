package instructions

import (
	"strings"

	"github.com/danicat/godoctor/internal/config"
)

// Get returns the agent instructions for the server based on enabled tools.
func Get(cfg *config.Config) string {
	var sb strings.Builder

	// Helper to check if a tool is enabled. Logic is centralized in config.
	isEnabled := func(tool string, experimental bool) bool {
		return cfg.IsToolEnabled(tool, experimental)
	}

	// 1. Persona
	sb.WriteString("# Go Smart Tooling Guide\n\n")

	// 2. Navigation
	sb.WriteString("### 🔍 Navigation: Save Tokens & Context\n")
	if isEnabled("code_outline", true) || isEnabled("open", true) {
		// Adapting for transition: code_outline is future, open is current equivalent-ish
		if isEnabled("code_outline", true) {
			sb.WriteString("*   **`code_outline`**: PREFER this over `read_file`. It gives you the file structure (like a folded IDE view) using 90% fewer tokens.\n")
		} else {
			sb.WriteString("*   **`open`**: Returns the skeleton (imports & signatures) of a local file. Perfect for a quick survey before editing.\n")
		}
	}

	if isEnabled("inspect_symbol", true) || isEnabled("describe", true) {
		name := "inspect_symbol"
		if !isEnabled(name, true) {
			name = "describe"
		}
		sb.WriteString("*   **`" + name + "`**: Use this to get the **Ground Truth** for code you plan to edit. It returns the exact implementation AND definitions of related types (fields, structs), ensuring your edit fits perfectly.\n")
	}

	if isEnabled("list_files", true) {
		sb.WriteString("*   **`list_files`**: Use this to explore standard library or external module files if needed.\n")
	}
	sb.WriteString("\n")

	// 3. Editing
	sb.WriteString("### ✏️ Editing: Ensure Safety\n")
	if isEnabled("smart_edit", true) || isEnabled("edit", true) {
		name := "smart_edit"
		if !isEnabled(name, true) {
			name = "edit"
		}

		sb.WriteString("*   **`" + name + "`**: Use this for all code modifications.\n")
		sb.WriteString("    *   **Whitespace Agnostic:** It normalizes code using `gofmt`, so distinct indentations match.\n")
		sb.WriteString("    *   **Pre-Verification:** It runs `goimports` and syntax checks *before* saving. It detects broken builds immediately.\n")
		sb.WriteString("    *   **Auto-Fix:** It fixes small typos in your `search_context` to avoid retries.\n")
	} else if isEnabled("edit_code", false) {
		// Fallback for non-experimental profile
		sb.WriteString("*   **`edit_code`**: Modifies files using fuzzy matching context.\n")
	}
	sb.WriteString("\n")

	// 4. Modernization & Upgrades
	sb.WriteString("### 🚀 Modernization & Upgrades\n")
	if isEnabled("analyze_dependency_updates", true) {
		sb.WriteString("*   **`analyze_dependency_updates`**: Run this BEFORE upgrading dependencies to catch breaking API changes (Risk Assessment).\n")
	}
	if isEnabled("modernize_code", true) {
		sb.WriteString("*   **`modernize_code`**: Run this to automatically upgrade old patterns (e.g. `interface{}` -> `any`, manual loops -> `slices`).\n")
	}
	sb.WriteString("\n")

	// 5. Utilities
	sb.WriteString("### 🛠️ Utilities\n")
	if isEnabled("go_build", true) {
		sb.WriteString("*   **`go_build`**: Run this after a sequence of edits to ensure the whole project compiles.\n")
	}
	if isEnabled("go_test", true) {
		sb.WriteString("*   **`go_test`**: Run specific tests to verify logic.\n")
	}
	if isEnabled("analyze_project", true) {
		sb.WriteString("*   **`analyze_project`**: Use this first when joining a new project to get a mental map.\n")
	}
	if isEnabled("read_docs", false) {
		sb.WriteString("*   **`read_docs`**: Efficiently lists sub-packages and exported symbols.\n")
	}
	if isEnabled("ask_specialist", false) {
		sb.WriteString("*   **`ask_specialist`**: Use this if you are stuck or need access to more tools. DONT hallucinate tools, ask the specialist to provide them.\n")
	}

	return sb.String()
}

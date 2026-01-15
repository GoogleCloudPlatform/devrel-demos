package instructions

import (
	"strings"

	"github.com/danicat/godoctor/internal/config"
	"github.com/danicat/godoctor/internal/toolnames"
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
			sb.WriteString(toolnames.Registry["code_outline"].Instruction + "\n")
		} else {
			sb.WriteString(toolnames.Registry["open"].Instruction + "\n")
		}
	}

	if isEnabled("inspect_symbol", true) || isEnabled("describe", true) {
		name := "inspect_symbol"
		if !isEnabled(name, true) {
			name = "describe" // Fallback, though registry key is inspect_symbol. Assuming 'describe' is legacy config key but tool name is standard.
			// Actually, if config key is 'describe', we might need a fallback lookup, but let's stick to standard names in registry.
		}
		// We use the registry instruction for inspect_symbol regardless of the legacy config name, 
		// as long as the intent is the same. The instruction text in registry uses "inspect_symbol".
		// If the user sees "describe" in the tool list (from MCP), but instructions say "inspect_symbol", that's a mismatch.
		// However, I'm refactoring the tool definitions too, so the tool name WILL be "inspect_symbol".
		sb.WriteString(toolnames.Registry["inspect_symbol"].Instruction + "\n")
	}

	if isEnabled("list_files", true) {
		sb.WriteString(toolnames.Registry["list_files"].Instruction + "\n")
	}
	sb.WriteString("\n")

	// 3. Editing
	sb.WriteString("### ✏️ Editing: Ensure Safety\n")
	if isEnabled("smart_edit", true) || isEnabled("edit", true) {
		// Prioritize smart_edit
		sb.WriteString(toolnames.Registry["smart_edit"].Instruction + "\n")
	} else if isEnabled("edit_code", false) {
		// Fallback for non-experimental profile
		sb.WriteString(toolnames.Registry["edit_code"].Instruction + "\n")
	}
	sb.WriteString("\n")

	// 4. Modernization & Upgrades
	sb.WriteString("### 🚀 Modernization & Upgrades\n")
	if isEnabled("analyze_dependency_updates", true) {
		sb.WriteString(toolnames.Registry["analyze_dependency_updates"].Instruction + "\n")
	}
	if isEnabled("modernize_code", true) || isEnabled("modernize", true) {
		sb.WriteString(toolnames.Registry["modernize"].Instruction + "\n")
	}
	sb.WriteString("\n")

	// 5. Utilities
	sb.WriteString("### 🛠️ Utilities\n")
	if isEnabled("go_build", true) {
		sb.WriteString(toolnames.Registry["go_build"].Instruction + "\n")
	}
	if isEnabled("go_test", true) {
		sb.WriteString(toolnames.Registry["go_test"].Instruction + "\n")
	}
	if isEnabled("analyze_project", true) {
		sb.WriteString(toolnames.Registry["analyze_project"].Instruction + "\n")
	}
	if isEnabled("read_docs", false) {
		sb.WriteString(toolnames.Registry["read_docs"].Instruction + "\n")
	}
	if isEnabled("ask_specialist", false) {
		sb.WriteString(toolnames.Registry["ask_specialist"].Instruction + "\n")
	}

	return sb.String()
}

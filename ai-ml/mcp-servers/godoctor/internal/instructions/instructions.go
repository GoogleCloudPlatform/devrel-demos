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
	isEnabled := func(tool string) bool {
		return cfg.IsToolEnabled(tool)
	}

	// 1. Persona
	sb.WriteString("# Go Smart Tooling Guide\n\n")

	// 2. Navigation
	sb.WriteString("### 🔍 Navigation: Save Tokens & Context\n")
	if isEnabled("file_outline") {
		sb.WriteString(toolnames.Registry["file_outline"].Instruction + "\n")
	}

	if isEnabled("symbol_inspect") {
		sb.WriteString(toolnames.Registry["symbol_inspect"].Instruction + "\n")
	}

	if isEnabled("file_list") {
		sb.WriteString(toolnames.Registry["file_list"].Instruction + "\n")
	}
	sb.WriteString("\n")

	// 3. Editing
	sb.WriteString("### ✏️ Editing: Ensure Safety\n")
	if isEnabled("file_edit") {
		sb.WriteString(toolnames.Registry["file_edit"].Instruction + "\n")
	}
	sb.WriteString("\n")

	// 4. Modernization & Upgrades
	sb.WriteString("### 🚀 Modernization & Upgrades\n")
	if isEnabled("go_diff") {
		sb.WriteString(toolnames.Registry["go_diff"].Instruction + "\n")
	}
	if isEnabled("go_modernize") {
		sb.WriteString(toolnames.Registry["go_modernize"].Instruction + "\n")
	}
	sb.WriteString("\n")

	// 5. Utilities
	sb.WriteString("### 🛠️ Utilities\n")
	if isEnabled("go_build") {
		sb.WriteString(toolnames.Registry["go_build"].Instruction + "\n")
	}
	if isEnabled("go_test") {
		sb.WriteString(toolnames.Registry["go_test"].Instruction + "\n")
	}
	if isEnabled("go_docs") {
		sb.WriteString(toolnames.Registry["go_docs"].Instruction + "\n")
	}
	if isEnabled("safe_shell") {
		sb.WriteString(toolnames.Registry["safe_shell"].Instruction + "\n")
	}

	return sb.String()
}

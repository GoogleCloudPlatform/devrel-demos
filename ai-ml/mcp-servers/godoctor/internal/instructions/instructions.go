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
	if isEnabled("file.outline", true) {
		// Adapting for transition: code_outline is future, open is current equivalent-ish
		sb.WriteString(toolnames.Registry["file.outline"].Instruction + "\n")
	}

	if isEnabled("symbol.inspect", true) {
		sb.WriteString(toolnames.Registry["symbol.inspect"].Instruction + "\n")
	}

	if isEnabled("file.list", true) {
		sb.WriteString(toolnames.Registry["file.list"].Instruction + "\n")
	}
	sb.WriteString("\n")

	// 3. Editing
	sb.WriteString("### ✏️ Editing: Ensure Safety\n")
	if isEnabled("file.edit", true) {
		// Prioritize smart_edit
		sb.WriteString(toolnames.Registry["file.edit"].Instruction + "\n")
	} else if isEnabled("file.edit_legacy", false) {
		// Fallback for non-experimental profile
		sb.WriteString(toolnames.Registry["file.edit_legacy"].Instruction + "\n")
	}
	sb.WriteString("\n")

	// 4. Modernization & Upgrades
	sb.WriteString("### 🚀 Modernization & Upgrades\n")
	if isEnabled("go.diff", true) {
		sb.WriteString(toolnames.Registry["go.diff"].Instruction + "\n")
	}
	if isEnabled("go.modernize", true) {
		sb.WriteString(toolnames.Registry["go.modernize"].Instruction + "\n")
	}
	sb.WriteString("\n")

	// 5. Utilities
	sb.WriteString("### 🛠️ Utilities\n")
	if isEnabled("go.build", true) {
		sb.WriteString(toolnames.Registry["go.build"].Instruction + "\n")
	}
	if isEnabled("go.test", true) {
		sb.WriteString(toolnames.Registry["go.test"].Instruction + "\n")
	}
	if isEnabled("project.map", true) {
		sb.WriteString(toolnames.Registry["project.map"].Instruction + "\n")
	}
	if isEnabled("go.docs", false) {
		sb.WriteString(toolnames.Registry["go.docs"].Instruction + "\n")
	}
	if isEnabled("agent.specialist", false) {
		sb.WriteString(toolnames.Registry["agent.specialist"].Instruction + "\n")
	}

	return sb.String()
}

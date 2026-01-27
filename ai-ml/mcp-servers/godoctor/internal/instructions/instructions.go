// Package instructions generates dynamic system instructions for the AI agent.
// It tailors the guidance provided to the LLM based on the currently enabled tools and configuration,
// ensuring the agent is aware of its capabilities and how to use them effectively.
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
	if isEnabled("smart_read") {
		sb.WriteString(toolnames.Registry["smart_read"].Instruction + "\n")
	}

	if isEnabled("list_files") {
		sb.WriteString(toolnames.Registry["list_files"].Instruction + "\n")
	}
	sb.WriteString("\n")

	// 3. Editing
	sb.WriteString("### ✏️ Editing: Ensure Safety\n")
	if isEnabled("smart_edit") {
		sb.WriteString(toolnames.Registry["smart_edit"].Instruction + "\n")
	}
	sb.WriteString("\n")

	// 4. Modernization & Upgrades
	sb.WriteString("### 🚀 Modernization & Upgrades\n")
	if isEnabled("check_api") {
		sb.WriteString(toolnames.Registry["check_api"].Instruction + "\n")
	}
	if isEnabled("modernize_code") {
		sb.WriteString(toolnames.Registry["modernize_code"].Instruction + "\n")
	}
	sb.WriteString("\n")

	// 5. Utilities
	sb.WriteString("### 🛠️ Utilities\n")
	if isEnabled("verify_build") {
		sb.WriteString(toolnames.Registry["verify_build"].Instruction + "\n")
	}
	if isEnabled("verify_tests") {
		sb.WriteString(toolnames.Registry["verify_tests"].Instruction + "\n")
	}
	if isEnabled("go_docs") {
		sb.WriteString(toolnames.Registry["go_docs"].Instruction + "\n")
	}

	return sb.String()
}

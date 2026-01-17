package shared

import (
	"strings"

	"golang.org/x/tools/go/packages"
)

// MCPRelatedErrors contains common strings found in MCP-related compilation errors.
var MCPRelatedErrors = []string{
	"mcp.ToolDefinition",
	"mcp.ToolCallRequest",
	"mcp.ToolCallResponse",
	"mcp.ToolContent",
	"mcp.NewServer",
	"mcp.Implementation",
	"mcp.ServerOptions",
	"RegisterTool",
	"ListenAndServe",
	"mcp.NewStdioServer",
	"github.com/modelcontextprotocol/go-sdk/mcp",
	"undefined: mcp",
}

// GetMCPHint checks a list of package errors for MCP-related issues and returns a hint if found.
func GetMCPHint(errs []packages.Error) string {
	for _, e := range errs {
		for _, pattern := range MCPRelatedErrors {
			if strings.Contains(e.Msg, pattern) {
				return "\n\n**HINT:** It looks like you're having trouble with the 'mcp' package. Try calling `go.docs` on \"github.com/modelcontextprotocol/go-sdk/mcp\" to see the correct API."
			}
		}
	}
	return ""
}

// GetMCPHintFromOutput checks a raw output string for MCP-related issues and returns a hint if found.
func GetMCPHintFromOutput(output string) string {
	for _, pattern := range MCPRelatedErrors {
		if strings.Contains(output, pattern) {
			return "\n\n**HINT:** It looks like you're having trouble with the 'mcp' package. Try calling `go.docs` on \"github.com/modelcontextprotocol/go-sdk/mcp\" to see the correct API."
		}
	}
	return ""
}

// CleanError strips noisy artifacts from Go compiler errors, such as empty name quotes.
func CleanError(msg string) string {
	// Remove the literal '("" )' or ': ""' artifacts that confuse agents.
	msg = strings.ReplaceAll(msg, `(invalid package name: "")`, `(invalid package name)`)
	msg = strings.ReplaceAll(msg, `invalid package name: ""`, `invalid package name`)
	return msg
}

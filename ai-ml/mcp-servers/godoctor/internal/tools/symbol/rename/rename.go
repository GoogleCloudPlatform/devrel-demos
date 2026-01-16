// Package rename implements the symbol renaming tool.
package rename

import (
	"context"
	"fmt"
	"os/exec"

	"github.com/danicat/godoctor/internal/toolnames"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Register registers the tool with the server.
func Register(server *mcp.Server) {
	def := toolnames.Registry["symbol.rename"]
	mcp.AddTool(server, &mcp.Tool{
		Name:        def.ExternalName,
		Title:       def.Title,
		Description: def.Description,
	}, toolHandler)
}

// Params defines the input parameters.
type Params struct {
	File    string `json:"file" jsonschema:"File containing the identifier to rename"`
	Line    int    `json:"line" jsonschema:"Line number (1-based)"`
	Col     int    `json:"col" jsonschema:"Column number (1-based)"`
	NewName string `json:"new_name" jsonschema:"The new name for the identifier"`
}

func toolHandler(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	// Check for gopls
	if _, err := exec.LookPath("gopls"); err != nil {
		return errorResult("Tool 'gopls' not found. Please install: go install golang.org/x/tools/gopls@latest"), nil, nil
	}

	if args.File == "" || args.NewName == "" || args.Line < 1 || args.Col < 1 {
		return errorResult("Invalid arguments: file, new_name, line (>0), and col (>0) are required"), nil, nil
	}

	location := fmt.Sprintf("%s:%d:%d", args.File, args.Line, args.Col)

	//nolint:gosec // G204: Subprocess launched with variable is expected behavior.
	cmd := exec.CommandContext(ctx, "gopls", "rename", "-w", location, args.NewName)
	// Run in project root (or file dir?)
	// gopls needs to run where go.mod is visible usually.
	// We assume current working directory is the project root.

	out, err := cmd.CombinedOutput()
	output := string(out)

	if err != nil {
		return errorResult(fmt.Sprintf("gopls rename failed: %v\nOutput: %s", err, output)), nil, nil
	}

	if output == "" {
		output = fmt.Sprintf("Successfully renamed symbol at %s to %s", location, args.NewName)
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: output},
		},
	}, nil, nil
}

func errorResult(msg string) *mcp.CallToolResult {
	return &mcp.CallToolResult{
		IsError: true,
		Content: []mcp.Content{
			&mcp.TextContent{Text: msg},
		},
	}
}

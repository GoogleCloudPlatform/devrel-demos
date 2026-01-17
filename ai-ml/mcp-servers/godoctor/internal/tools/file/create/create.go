// Package create implements the file creation tool.
package create

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/danicat/godoctor/internal/graph"
	"github.com/danicat/godoctor/internal/toolnames"
	"github.com/danicat/godoctor/internal/tools/shared"
	"github.com/modelcontextprotocol/go-sdk/mcp"
	"golang.org/x/tools/imports"
)

// Register registers the write tool with the server.
func Register(server *mcp.Server) {
	def := toolnames.Registry["file.create"]
	mcp.AddTool(server, &mcp.Tool{
		Name:        def.ExternalName,
		Title:       def.Title,
		Description: def.Description,
	}, toolHandler)
}

// Params defines the input parameters for the write tool.
type Params struct {
	Filename string `json:"filename" jsonschema:"The path to the file to create"`
	Content  string `json:"content" jsonschema:"The content to write"`
}

func toolHandler(_ context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	if args.Filename == "" {
		return errorResult("name (file path) cannot be empty"), nil, nil
	}

	finalContent := []byte(args.Content)
	var warning string

	// 1. Auto-Format & Import check (GO ONLY)
	if strings.HasSuffix(args.Filename, ".go") {
		formatted, err := imports.Process(args.Filename, finalContent, nil)
		if err != nil {
			return errorResult(fmt.Sprintf("write produced invalid Go code: %v", err)), nil, nil
		}
		finalContent = formatted
	}

	// 2. Ensure directory exists
	//nolint:gosec // G301: Standard permissions for source directories.
	if err := os.MkdirAll(filepath.Dir(args.Filename), 0755); err != nil {
		return errorResult(fmt.Sprintf("failed to create directory: %v", err)), nil, nil
	}

	// 3. Write to disk
	//nolint:gosec // G306: Standard permissions for source files.
	if err := os.WriteFile(args.Filename, finalContent, 0644); err != nil {
		return errorResult(fmt.Sprintf("failed to write file: %v", err)), nil, nil
	}

	// 4. Post-Check Verification (GO ONLY)
	if strings.HasSuffix(args.Filename, ".go") {
		pkg, err := graph.Global.Load(args.Filename)
		if err == nil && len(pkg.Errors) > 0 {
			warning = "\n\n**WARNING:** Write successful but introduced errors:\n"
			for _, e := range pkg.Errors {
				loc := ""
				if e.Pos != "" {
					loc = e.Pos + ": "
				}
				warning += fmt.Sprintf("- %s%s\n", loc, shared.CleanError(e.Msg))
			}
			warning += shared.GetMCPHint(pkg.Errors)
		}
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: fmt.Sprintf("Successfully wrote %s%s", args.Filename, warning)},
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

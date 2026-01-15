package create

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/danicat/godoctor/internal/graph"
	"github.com/danicat/godoctor/internal/toolnames"
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
	Name    string `json:"name" jsonschema:"The path to the file to write"`
	Content string `json:"content" jsonschema:"The content to write"`
}

func toolHandler(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	if args.Name == "" {
		return errorResult("name (file path) cannot be empty"), nil, nil
	}
	if !strings.HasSuffix(args.Name, ".go") {
		return errorResult("file must be a Go file (*.go)"), nil, nil
	}

	finalContent := []byte(args.Content)

	// 1. Auto-Format & Import check
	formatted, err := imports.Process(args.Name, finalContent, nil)
	if err != nil {
		return errorResult(fmt.Sprintf("write produced invalid Go code: %v", err)), nil, nil
	}

	// 2. Ensure directory exists
	if err := os.MkdirAll(filepath.Dir(args.Name), 0755); err != nil {
		return errorResult(fmt.Sprintf("failed to create directory: %v", err)), nil, nil
	}

	// 3. Write to disk
	if err := os.WriteFile(args.Name, formatted, 0644); err != nil {
		return errorResult(fmt.Sprintf("failed to write file: %v", err)), nil, nil
	}

	// 4. Post-Check Verification
	pkg, err := graph.Global.Load(args.Name)
	var warning string
	if err == nil && len(pkg.Errors) > 0 {
		warning = "\n\n**WARNING:** Write successful but introduced errors:\n"
		for _, e := range pkg.Errors {
			warning += fmt.Sprintf("- %s\n", e.Msg)
		}
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: fmt.Sprintf("Successfully wrote %s%s", args.Name, warning)},
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

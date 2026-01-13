// Package read_docs implements the documentation retrieval tool.
package read_docs

import (
	"context"
	"fmt"

	"github.com/danicat/godoctor/internal/godoc"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Register registers the read_docs tool with the server.
func Register(server *mcp.Server) {
	mcp.AddTool(server, &mcp.Tool{
		Name:        "read_docs",
		Title:       "Read Go Documentation (Map Module)",
		Description: "The high-level map builder. Lists all sub-packages and exported symbols in a module. Use this FIRST to visualize the codebase structure without flooding your context window.",
	}, ToolHandler)
}

// Params defines the input parameters for the read_docs tool.
type Params struct {
	PackagePath string `json:"package_path"`
	SymbolName  string `json:"symbol_name,omitempty"`
}

// ToolHandler handles the read_docs tool execution.
func ToolHandler(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	if args.PackagePath == "" {
		return &mcp.CallToolResult{
			IsError: true,
			Content: []mcp.Content{
				&mcp.TextContent{Text: "package_path cannot be empty"},
			},
		}, nil, nil
	}

	markdown, err := godoc.GetDocumentation(ctx, args.PackagePath, args.SymbolName)
	if err != nil {
		return &mcp.CallToolResult{
			IsError: true,
			Content: []mcp.Content{
				&mcp.TextContent{Text: fmt.Sprintf("failed to read documentation: %v", err)},
			},
		}, nil, nil
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: markdown},
		},
	}, nil, nil
}

// Package read_docs implements the documentation retrieval tool.
package docs

import (
	"context"
	"encoding/json"
	"fmt"
	"strings"

	"github.com/danicat/godoctor/internal/godoc"
	"github.com/danicat/godoctor/internal/toolnames"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Register registers the read_docs tool with the server.
func Register(server *mcp.Server) {
	def := toolnames.Registry["go.docs"]
	mcp.AddTool(server, &mcp.Tool{
		Name:        def.ExternalName,
		Title:       def.Title,
		Description: def.Description,
	}, Handler)
}

// Params defines the input parameters for the read_docs tool.
type Params struct {
	PackagePath string `json:"package_path" jsonschema:"Import path of the package (e.g. 'fmt')"`
	SymbolName  string `json:"symbol_name,omitempty" jsonschema:"Optional symbol name to lookup"`
	Format      string `json:"format,omitempty" jsonschema:"Output format: 'markdown' (default) or 'json'"`
}

// Handler handles the read_docs tool execution.
func Handler(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	if args.PackagePath == "" {
		return &mcp.CallToolResult{
			IsError: true,
			Content: []mcp.Content{
				&mcp.TextContent{Text: "package_path cannot be empty"},
			},
		}, nil, nil
	}

	// Default to markdown
	if args.Format == "" {
		args.Format = "markdown"
	}
	args.Format = strings.ToLower(args.Format)
	if args.Format != "markdown" && args.Format != "json" {
		return &mcp.CallToolResult{
			IsError: true,
			Content: []mcp.Content{
				&mcp.TextContent{Text: "invalid format: must be 'markdown' or 'json'"},
			},
		}, nil, nil
	}

	// Use GetStructuredDoc for flexibility
	doc, err := godoc.GetStructuredDoc(ctx, args.PackagePath, args.SymbolName)
	if err != nil {
		return &mcp.CallToolResult{
			IsError: true,
			Content: []mcp.Content{
				&mcp.TextContent{Text: fmt.Sprintf("failed to read documentation: %v", err)},
			},
		}, nil, nil
	}

	var output string

	if args.Format == "json" {
		bytes, err := json.MarshalIndent(doc, "", "  ")
		if err != nil {
			return &mcp.CallToolResult{
				IsError: true,
				Content: []mcp.Content{
					&mcp.TextContent{Text: fmt.Sprintf("failed to marshal JSON: %v", err)},
				},
			}, nil, nil
		}
		output = string(bytes)
	} else {
		// Render logic duplicated from godoc.GetDocumentation?
		// No, use godoc.Render
		output = godoc.Render(doc)
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: output},
		},
	}, nil, nil
}

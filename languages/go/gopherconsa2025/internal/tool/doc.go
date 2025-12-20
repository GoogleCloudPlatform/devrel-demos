package tool

import (
	"context"
	"fmt"
	"log"
	"os/exec"

	"github.com/modelcontextprotocol/go-sdk/jsonschema"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// GoDocTool defines the schema for the go-doc tool.
func GoDocTool() *mcp.Tool {
	return &mcp.Tool{
		Name:        "go-doc",
		Description: "Retrieves Go documentation for a specified package and, optionally, a specific symbol within that package.",
		InputSchema: &jsonschema.Schema{
			Type: "object",
			Properties: map[string]*jsonschema.Schema{
				"package_path": {
					Type:        "string",
					Description: "The Go package path (e.g., 'fmt', 'net/http').",
				},
				"symbol_name": {
					Type:        "string",
					Description: "Optional: The symbol name within the package (e.g., 'Println', 'Server').",
				},
			},
			Required: []string{"package_path"},
		},
	}
}

// GoDocHandler is the handler for the go-doc tool.
func GoDocHandler(ctx context.Context, session *mcp.ServerSession, params *mcp.CallToolParamsFor[map[string]any]) (*mcp.CallToolResultFor[any], error) {
	log.SetFlags(log.Ltime | log.Lshortfile)
	log.Printf("Executing go-doc tool with parameters: %v", params.Arguments)

	packagePath, ok := params.Arguments["package_path"].(string)
	if !ok || packagePath == "" {
		return nil, fmt.Errorf("required parameter 'package_path' is missing or not a string")
	}

	args := []string{"doc"}
	if symbolName, ok := params.Arguments["symbol_name"].(string); ok && symbolName != "" {
		args = append(args, packagePath, symbolName)
	} else {
		args = append(args, packagePath)
	}

	cmd := exec.CommandContext(ctx, "go", args...)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return &mcp.CallToolResultFor[any]{
			IsError: true,
			Content: []mcp.Content{
				&mcp.TextContent{
					Text: fmt.Sprintf("failed to execute 'go doc': %v, output: %s", err, string(output)),
				},
			},
		}, nil
	}

	return &mcp.CallToolResultFor[any]{
		Content: []mcp.Content{
			&mcp.TextContent{
				Text: string(output),
			},
		},
	}, nil
}
package main

import (
	"context"
	"fmt"
	"os"

	"github.com/modelcontextprotocol/go-sdk/server"
	"github.com/modelcontextprotocol/go-sdk/transport/stdio"
	"github.com/modelcontextprotocol/go-sdk/types"
)

func main() {
	s := server.NewServer(
		types.Implementation{
			Name:    "example-server",
			Version: "0.1.0",
		},
		server.ServerOptions{
			Capabilities: types.ServerCapabilities{
				Tools: &types.ServerToolsCapabilities{},
			},
		},
	)

	s.RegisterTool(
		types.Tool{
			Name:        "hello",
			Description: "Say hello",
			InputSchema: types.ToolInputSchema{
				Type: "object",
				Properties: map[string]interface{}{
					"name": map[string]interface{}{
						"type": "string",
					},
				},
			},
		},
		func(ctx context.Context, request types.CallToolRequest) (*types.CallToolResult, error) {
			name, ok := request.Arguments["name"].(string)
			if !ok {
				name = "World"
			}
			return &types.CallToolResult{
				Content: []types.Content{
					types.TextContent{
						Type: "text",
						Text: fmt.Sprintf("Hello, %s!", name),
					},
				},
			}, nil
		},
	)

	// Start the server using stdio transport
	if err := s.Serve(stdio.NewTransport()); err != nil {
		fmt.Fprintf(os.Stderr, "Server error: %v
", err)
		os.Exit(1)
	}
}

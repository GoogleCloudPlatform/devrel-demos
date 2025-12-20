package main

import (
	"context"
	"log"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func main() {
	// Create a new MCP server.
	server := mcp.NewServer(&mcp.Implementation{Name: "hello-world-server"}, nil)

	// Define the arguments for the "hello" tool.
	type helloArgs struct {
		Name string `json:"name" jsonschema:"the name to say hello to"`
	}

	// Add the "hello" tool to the server.
	mcp.AddTool(server, &mcp.Tool{
		Name:        "hello",
		Description: "A simple hello world tool",
	}, func(ctx context.Context, req *mcp.CallToolRequest, args helloArgs) (*mcp.CallToolResult, any, error) {
		return &mcp.CallToolResult{
			Content: []mcp.Content{
				&mcp.TextContent{Text: "Hello, " + args.Name},
			},
		}, nil, nil
	})

	// Run the server on the stdio transport.
	if err := server.Run(context.Background(), &mcp.StdioTransport{}); err != nil {
		log.Printf("Server failed: %v", err)
	}
}
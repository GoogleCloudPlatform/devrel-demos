package main

import (
	"context"
	"fmt"
	"os"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func run() error {
	server := mcp.NewServer(&mcp.Implementation{Name: "godoctor"}, nil)

	mcp.AddTool[any, any](server, &mcp.Tool{
		Name:        "hello",
		Description: "A simple hello world tool",
	}, func(ctx context.Context, req *mcp.CallToolRequest, params any) (*mcp.CallToolResult, any, error) {
		return &mcp.CallToolResult{
			Content: []mcp.Content{
				&mcp.TextContent{Text: "Hello, World!"},
			},
		}, nil, nil
	})

	return server.Run(context.Background(), &mcp.StdioTransport{})
}
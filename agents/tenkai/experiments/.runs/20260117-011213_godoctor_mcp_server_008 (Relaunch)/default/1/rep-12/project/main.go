package main

import (
	"context"
	"io"
	"log"
	"os"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func helloWorldTool(ctx context.Context, req *mcp.CallToolRequest, args any) (*mcp.CallToolResult, any, error) {
	log.Printf("Tool call: hello_world")
	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: "Hello from Tenkai!"},
		},
	}, nil, nil
}

func runServer(ctx context.Context, transport mcp.Transport) error {
	server := mcp.NewServer(&mcp.Implementation{Name: "hello-tenkai"}, nil)

	mcp.AddTool(server, &mcp.Tool{
		Name:        "hello_world",
		Description: "Returns a hello message",
	}, helloWorldTool)

	log.Printf("Starting server...")
	err := server.Run(ctx, transport)
	log.Printf("Server stopped.")
	return err
}

func main() {
	// Create a log file to trace I/O
	logFile, err := os.OpenFile("mcp-trace.log", os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0666)
	if err != nil {
		log.Fatalf("failed to open log file: %v", err)
	}
	defer logFile.Close()
	log.SetOutput(io.MultiWriter(os.Stderr, logFile))

	if err := runServer(context.Background(), &mcp.StdioTransport{}); err != nil {
		log.Printf("Server failed: %v", err)
	}
}

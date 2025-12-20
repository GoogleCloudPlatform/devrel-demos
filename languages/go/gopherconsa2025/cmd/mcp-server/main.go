package main

import (
	"context"
	"log"

	"gopherconsa25.com/mcp-go-doc/internal/tool"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func main() {
	ctx := context.Background()
	server := mcp.NewServer(
		&mcp.Implementation{
			Name: "go-doc-server",
		},
		nil,
	)

	mcp.AddTool(server, tool.GoDocTool(), tool.GoDocHandler)

	transport := mcp.NewStdioTransport()
	session, err := server.Connect(ctx, transport)
	if err != nil {
		log.Fatalf("failed to connect to transport: %v", err)
	}
	defer session.Close()

	log.Println("MCP server started and waiting for requests...")
	if err := session.Wait(); err != nil {
		log.Fatalf("session ended with error: %v", err)
	}
}
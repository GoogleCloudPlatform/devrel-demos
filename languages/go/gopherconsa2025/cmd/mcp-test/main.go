package main

import (
	"context"
	"fmt"
	"log"
	"os/exec"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func main() {
	// Server
	go func() {
		server := mcp.NewServer(
			&mcp.Implementation{
				Tools: map[string]mcp.Tool{
					"test": {
						Execute: func(ctx context.Context, request mcp.ExecuteToolRequest) (mcp.ExecuteToolResponse, error) {
							return mcp.ExecuteToolResponse{
								Result: "Hello from the server!",
							}, nil
						},
					},
				},
			},
			nil,
		)
		if err := server.Start(context.Background(), mcp.NewStdioTransport()); err != nil {
			log.Fatalf("server error: %v", err)
		}
	}()

	// Client
	client := mcp.NewClient(
		&mcp.Implementation{},
		nil,
	)
	session, err := client.Connect(context.Background(), mcp.NewCommandTransport(exec.Command("go", "run", "cmd/mcp-test/main.go")))
	if err != nil {
		log.Fatalf("client error: %v", err)
	}
	defer session.Close()

	response, err := session.CallTool(context.Background(), &mcp.CallToolParams{
		Name: "test",
	})
	if err != nil {
		log.Fatalf("tool error: %v", err)
	}

	fmt.Println(response.Result)
}

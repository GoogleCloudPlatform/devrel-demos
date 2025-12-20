package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os/exec"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func main() {
	packagePath := flag.String("package_path", "", "The Go package path (e.g., 'fmt', 'net/http').")
	symbolName := flag.String("symbol_name", "", "Optional: The symbol name within the package (e.g., 'Println', 'Server').")
	flag.Parse()

	if *packagePath == "" {
		log.Fatal("Usage: go run cmd/mcp-client/main.go -package_path <path> [-symbol_name <symbol>]")
	}

	ctx := context.Background()
	client := mcp.NewClient(&mcp.Implementation{}, nil)

	cmd := exec.CommandContext(ctx, "go", "run", "gopherconsa25.com/mcp-go-doc/cmd/mcp-server")
	transport := mcp.NewCommandTransport(cmd)

	session, err := client.Connect(ctx, transport)
	if err != nil {
		log.Fatalf("Failed to connect to MCP server: %v", err)
	}
	defer session.Close()

	toolParameters := make(map[string]interface{})
	toolParameters["package_path"] = *packagePath
	if *symbolName != "" {
		toolParameters["symbol_name"] = *symbolName
	}

	response, err := session.CallTool(ctx, &mcp.CallToolParams{
		Name:      "go-doc",
		Arguments: toolParameters,
	})
	if err != nil {
		log.Fatalf("Failed to execute tool: %v", err)
	}

	prettyJSON, err := json.MarshalIndent(response, "", "  ")
	if err != nil {
		log.Fatalf("Failed to format JSON: %v", err)
	}

	fmt.Println(string(prettyJSON))
}
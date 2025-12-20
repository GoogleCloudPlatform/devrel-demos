package main

import (
	"context"
	"log"
	"os/exec"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func main() {
	server := mcp.NewServer(&mcp.Implementation{Name: "hello-world-server"}, nil)

	type helloArgs struct {
		Name string `json:"name" jsonschema:"the person to greet"`
	}

	mcp.AddTool(server, &mcp.Tool{
		Name:        "hello",
		Description: "say hi",
	}, func(ctx context.Context, req *mcp.CallToolRequest, args helloArgs) (*mcp.CallToolResult, any, error) {
		return &mcp.CallToolResult{
			Content: []mcp.Content{
				&mcp.TextContent{Text: "Hello, " + args.Name},
			},
		}, nil, nil
	})

	type godocArgs struct {
		Package string `json:"package" jsonschema:"the package to document"`
		Symbol  string `json:"symbol,omitempty" jsonschema:"the symbol to document"`
	}

	mcp.AddTool(server, &mcp.Tool{
		Name:        "godoc",
		Description: "get Go documentation",
	}, func(ctx context.Context, req *mcp.CallToolRequest, args godocArgs) (*mcp.CallToolResult, any, error) {
		cmdArgs := []string{"doc"}
		if args.Package != "" {
			cmdArgs = append(cmdArgs, args.Package)
		}
		if args.Symbol != "" {
			cmdArgs = append(cmdArgs, args.Symbol)
		}
		cmd := exec.CommandContext(ctx, "go", cmdArgs...)
		out, err := cmd.CombinedOutput()
		if err != nil {
			return nil, nil, err
		}
		return &mcp.CallToolResult{
			Content: []mcp.Content{
				&mcp.TextContent{Text: string(out)},
			},
		}, nil, nil
	})

	if err := server.Run(context.Background(), &mcp.StdioTransport{}); err != nil {
		log.Printf("Server failed: %v", err)
	}
}

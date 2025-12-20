package main

import (
	"context"
	"log"
	"os/exec"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// GoDocParams defines the input parameters for the "go-doc" tool.
type GoDocParams struct {
	Package string `json:"package" jsonschema:"The Go package to document."`
	Symbol  string `json:"symbol,omitempty" jsonschema:"Optional: the symbol to document within the package."`
}

// GoDocHandler is the implementation of the "go-doc" tool.
func GoDocHandler(ctx context.Context, session *mcp.ServerSession, params *mcp.CallToolParamsFor[GoDocParams]) (*mcp.CallToolResultFor[any], error) {
	args := []string{"doc"}
	if params.Arguments.Package != "" {
		args = append(args, params.Arguments.Package)
	}
	if params.Arguments.Symbol != "" {
		args = append(args, params.Arguments.Symbol)
	}

	cmd := exec.CommandContext(ctx, "go", args...)
		output, err := cmd.CombinedOutput()
		if err != nil {
			return &mcp.CallToolResultFor[any]{
				Content: []mcp.Content{
					&mcp.TextContent{Text: "Error executing go doc: " + err.Error() + "\n" + string(output)},
				},
			}, nil
		}

	return &mcp.CallToolResultFor[any]{
		Content: []mcp.Content{
			&mcp.TextContent{Text: string(output)},
		},
	}, nil
}

// HelloWorldParams defines the input parameters for the "hello" tool.
// The `json` and `jsonschema` tags are used by the SDK to handle
// JSON serialization and generate the tool's input schema.
type HelloWorldParams struct {
	Name string `json:"name" jsonschema:"The name of the person to greet."`
}

// HelloWorldHandler is the implementation of the "hello" tool.
// It takes the tool's parameters and returns a text content response.
func HelloWorldHandler(ctx context.Context, session *mcp.ServerSession, params *mcp.CallToolParamsFor[HelloWorldParams]) (*mcp.CallToolResultFor[any], error) {
	greeting := "Hello, " + params.Arguments.Name + "!"
	return &mcp.CallToolResultFor[any]{
		Content: []mcp.Content{
			&mcp.TextContent{Text: greeting},
		},
	}, nil
}

func main() {
	// 1. Create a new MCP server implementation.
	server := mcp.NewServer(&mcp.Implementation{
		Name:    "godoctor",
		Version: "0.0.1",
	}, nil)

	// 2. Define the "hello" tool with its description.
	helloTool := &mcp.Tool{
		Name:        "hello",
		Description: "A simple tool that returns a greeting.",
	}

	// 3. Add the tool and its handler to the server.
	mcp.AddTool(server, helloTool, HelloWorldHandler)

	// 4. Define the "go-doc" tool.
	goDocTool := &mcp.Tool{
		Name:        "go-doc",
		Description: "Reads Go documentation for a package.",
	}
	mcp.AddTool(server, goDocTool, GoDocHandler)

	// 5. Create a stdio transport to communicate over stdin/stdout.
	transport := mcp.NewStdioTransport()

	// 6. Run the server over the stdio transport. This is a blocking call
	// that waits until the client disconnects.
	if err := server.Run(context.Background(), transport); err != nil {
		log.Fatalf("Server exited with error: %v", err)
	}
}

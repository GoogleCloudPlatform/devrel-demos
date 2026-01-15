package get

import (
	"context"
	"fmt"
	"os/exec"

	"github.com/danicat/godoctor/internal/toolnames"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Register registers the tool with the server.
func Register(server *mcp.Server) {
	def := toolnames.Registry["go.get"]
	mcp.AddTool(server, &mcp.Tool{
		Name:        def.ExternalName,
		Title:       def.Title,
		Description: def.Description,
	}, Handler)
}

// Params defines the input parameters.
type Params struct {
	Packages []string `json:"packages" jsonschema:"Packages to get (e.g. example.com/pkg@latest)"`
	Update   bool     `json:"update,omitempty" jsonschema:"If true, adds -u flag to update modules"`
}

func Handler(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	if len(args.Packages) == 0 {
		return &mcp.CallToolResult{
			IsError: true,
			Content: []mcp.Content{
				&mcp.TextContent{Text: "at least one package must be specified"},
			},
		}, nil, nil
	}

	cmdArgs := []string{"get"}
	if args.Update {
		cmdArgs = append(cmdArgs, "-u")
	}
	cmdArgs = append(cmdArgs, args.Packages...)

	cmd := exec.CommandContext(ctx, "go", cmdArgs...)
	// Run in current directory
	output, err := cmd.CombinedOutput()

	result := string(output)
	if err != nil {
		return &mcp.CallToolResult{
			IsError: true,
			Content: []mcp.Content{
				&mcp.TextContent{Text: fmt.Sprintf("go get failed: %v\nOutput:\n%s", err, result)},
			},
		}, nil, nil
	}

	if result == "" {
		result = fmt.Sprintf("Successfully ran 'go get %s'", fmt.Sprint(args.Packages))
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: result},
		},
	}, nil, nil
}

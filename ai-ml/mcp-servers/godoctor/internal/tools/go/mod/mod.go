package mod

import (
	"context"
	"fmt"
	"os/exec"

	"github.com/danicat/godoctor/internal/toolnames"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Register registers the tool with the server.
func Register(server *mcp.Server) {
	def := toolnames.Registry["go.mod"]
	mcp.AddTool(server, &mcp.Tool{
		Name:        def.ExternalName,
		Title:       def.Title,
		Description: def.Description,
	}, Handler)
}

// Params defines the input parameters.
type Params struct {
	Command string `json:"command" jsonschema:"The subcommand to run (e.g. 'tidy', 'download', 'verify'). Default: 'tidy'"`
}

func Handler(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	subCmd := args.Command
	if subCmd == "" {
		subCmd = "tidy"
	}

	// Whitelist allowed subcommands for safety?
	// go mod has: download, edit, graph, init, tidy, vendor, verify, why
	// Let's allow standard ones.
	switch subCmd {
	case "tidy", "download", "verify", "vendor":
		// ok
	default:
		return &mcp.CallToolResult{
			IsError: true,
			Content: []mcp.Content{
				&mcp.TextContent{Text: fmt.Sprintf("unsupported go mod subcommand: %s. Supported: tidy, download, verify, vendor", subCmd)},
			},
		}, nil, nil
	}

	cmd := exec.CommandContext(ctx, "go", "mod", subCmd)
	output, err := cmd.CombinedOutput()

	result := string(output)
	if err != nil {
		return &mcp.CallToolResult{
			IsError: true,
			Content: []mcp.Content{
				&mcp.TextContent{Text: fmt.Sprintf("go mod %s failed: %v\nOutput:\n%s", subCmd, err, result)},
			},
		}, nil, nil
	}

	if result == "" {
		result = fmt.Sprintf("Successfully ran 'go mod %s'", subCmd)
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: result},
		},
	}, nil, nil
}

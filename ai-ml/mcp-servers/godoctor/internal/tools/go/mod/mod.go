// Package mod implements the go mod tool.
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
	Command string   `json:"command" jsonschema:"The subcommand to run (e.g. 'tidy', 'init', 'edit', 'vendor', 'verify', 'why', 'graph', 'download'). Default: 'tidy'"`
	Args    []string `json:"args,omitempty" jsonschema:"Additional arguments for the subcommand (e.g. module name for 'init', package for 'why')"`
}

func Handler(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	subCmd := args.Command
	if subCmd == "" {
		subCmd = "tidy"
	}

	// Whitelist allowed subcommands for safety
	switch subCmd {
	case "tidy", "download", "verify", "vendor", "graph", "why", "edit", "init":
		// ok
	default:
		return &mcp.CallToolResult{
			IsError: true,
			Content: []mcp.Content{
				&mcp.TextContent{Text: fmt.Sprintf("unsupported go mod subcommand: %s. Supported: tidy, download, verify, vendor, graph, why, edit, init", subCmd)},
			},
		}, nil, nil
	}

	cmdArgs := append([]string{"mod", subCmd}, args.Args...)
	//nolint:gosec // G204: Subprocess launched with variable is expected behavior.
	cmd := exec.CommandContext(ctx, "go", cmdArgs...)
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
		result = fmt.Sprintf("Successfully ran 'go mod %s %v'", subCmd, args.Args)
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: result},
		},
	}, nil, nil
}

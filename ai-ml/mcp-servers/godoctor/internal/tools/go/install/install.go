// Package install implements the go install tool.
package install

import (
	"context"
	"fmt"
	"os/exec"

	"github.com/danicat/godoctor/internal/toolnames"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Register registers the tool with the server.
func Register(server *mcp.Server) {
	def := toolnames.Registry["go.install"]
	mcp.AddTool(server, &mcp.Tool{
		Name:        def.ExternalName,
		Title:       def.Title,
		Description: def.Description,
	}, Handler)
}

// Params defines the input parameters.
type Params struct {
	Dir      string   `json:"dir,omitempty" jsonschema:"Directory to install in (default: current)"`
	Packages []string `json:"packages,omitempty" jsonschema:"Packages to install (default: ./...)"`
	Args     []string `json:"args,omitempty" jsonschema:"Additional arguments (e.g. -v, -tags)"`
}

func Handler(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	dir := args.Dir
	if dir == "" {
		dir = "."
	}
	pkgs := args.Packages
	if len(pkgs) == 0 {
		pkgs = []string{"./..."}
	}

	cmdArgs := append([]string{"install"}, args.Args...)
	cmdArgs = append(cmdArgs, pkgs...)
	//nolint:gosec // G204: Subprocess launched with variable is expected behavior.
	cmd := exec.CommandContext(ctx, "go", cmdArgs...)
	cmd.Dir = dir

	out, err := cmd.CombinedOutput()
	output := string(out)

	if err != nil {
		if output == "" {
			output = fmt.Sprintf("Install failed: %v", err)
		} else {
			output = "Install Failed:\n" + output
		}
	} else {
		if output == "" {
			output = "Install Successful."
		} else {
			output = "Install Successful:\n" + output
		}
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: output},
		},
	}, nil, nil
}

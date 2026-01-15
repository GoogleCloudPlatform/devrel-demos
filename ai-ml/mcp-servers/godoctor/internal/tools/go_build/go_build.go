package go_build

import (
	"context"
	"fmt"
	"os/exec"

	"github.com/danicat/godoctor/internal/toolnames"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Register registers the tool with the server.
func Register(server *mcp.Server) {
	def := toolnames.Registry["go_build"]
	mcp.AddTool(server, &mcp.Tool{
		Name:        def.Name,
		Title:       def.Title,
		Description: def.Description,
	}, Handler)
}

// Params defines the input parameters.
type Params struct {
	Dir      string   `json:"dir,omitempty" jsonschema:"Directory to build in (default: current)"`
	Packages []string `json:"packages,omitempty" jsonschema:"Packages to build (default: ./...)"`
	Output   string   `json:"output,omitempty" jsonschema:"Output file name (-o flag). default: package name or module name"`
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

	cmdArgs := append([]string{"build"}, pkgs...)
	if args.Output != "" {
		// Output flag requires single package often, or strict rules if multiple.
		// If ./... is used, -o only works if output is a directory.
		cmdArgs = append([]string{"build", "-o", args.Output}, pkgs...)
	} else {
		cmdArgs = append([]string{"build"}, pkgs...)
	}

	cmd := exec.CommandContext(ctx, "go", cmdArgs...)
	cmd.Dir = dir

	out, err := cmd.CombinedOutput()
	output := string(out)

	if err != nil {
		if output == "" {
			output = fmt.Sprintf("Build failed: %v", err)
		} else {
			output = "Build Failed:\n" + output
		}
	} else {
		if output == "" {
			// Check if file exists if specific output?
			output = "Build Successful."
		} else {
			output = "Build Successful:\n" + output
		}
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: output},
		},
	}, nil, nil
}

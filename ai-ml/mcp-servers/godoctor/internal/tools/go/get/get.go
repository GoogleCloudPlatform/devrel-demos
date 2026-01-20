// Package get implements the go get tool.
package get

import (
	"context"
	"fmt"
	"os/exec"
	"strings"

	"github.com/danicat/godoctor/internal/godoc"
	"github.com/danicat/godoctor/internal/toolnames"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Register registers the tool with the server.
func Register(server *mcp.Server) {
	def := toolnames.Registry["go_get"]
	mcp.AddTool(server, &mcp.Tool{
		Name:        def.Name,
		Title:       def.Title,
		Description: def.Description,
	}, Handler)
}

// Params defines the input parameters.
type Params struct {
	Packages []string `json:"packages" jsonschema:"Packages to get (e.g. example.com/pkg@latest)"`
	Update   bool     `json:"update,omitempty" jsonschema:"If true, adds -u flag to update modules"`
	Args     []string `json:"args,omitempty" jsonschema:"Additional arguments (e.g. -t, -v)"`
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
	cmdArgs = append(cmdArgs, args.Args...)
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

	// Build success message
	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("Successfully ran 'go get %s'\n", strings.Join(args.Packages, " ")))

	// Auto-fetch documentation for each package
	for _, pkg := range args.Packages {
		// Strip version suffix if present (e.g., @latest, @v1.2.3)
		pkgPath := strings.Split(pkg, "@")[0]

		doc, err := godoc.Load(ctx, pkgPath, "")
		if err == nil && doc.Package != "" {
			sb.WriteString("\n")
			sb.WriteString(godoc.Render(doc))
		}
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: sb.String()},
		},
	}, nil, nil
}

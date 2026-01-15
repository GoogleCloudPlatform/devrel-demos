package diff

import (
	"context"
	"fmt"
	"os/exec"

	"github.com/danicat/godoctor/internal/toolnames"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Register registers the tool with the server.
func Register(server *mcp.Server) {
	def := toolnames.Registry["go.diff"]
	mcp.AddTool(server, &mcp.Tool{
		Name:        def.ExternalName,
		Title:       def.Title,
		Description: def.Description,
	}, toolHandler)
}

// Params defines the input parameters.
type Params struct {
	Old string `json:"old" jsonschema:"The old version (git revision, e.g. 'main', 'v1.0.0', or package path if comparing against local)"`
	New string `json:"new" jsonschema:"The new version (git revision, or '.' for local working copy)"`
	Dir string `json:"dir,omitempty" jsonschema:"Directory to run analysis in (default: current)"`
}

func toolHandler(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	// Check if apidiff is installed
	if _, err := exec.LookPath("apidiff"); err != nil {
		return errorResult("Tool 'apidiff' not found. Please install it: go install golang.org/x/exp/cmd/apidiff@latest"), nil, nil
	}

	if args.Old == "" || args.New == "" {
		return errorResult("both 'old' and 'new' revisions must be specified (use '.' for local)"), nil, nil
	}

	dir := args.Dir
	if dir == "" {
		dir = "."
	}

	cmd := exec.CommandContext(ctx, "apidiff", args.Old, args.New)
	cmd.Dir = dir

	out, err := cmd.CombinedOutput()
	output := string(out)

	if err != nil {
		// apidiff returns non-zero if changes found?
		// "Exit status 1 if there are incompatible changes".
		// So checking err might be misleading if we just want the report.
		// If output is non-empty, it's likely the report.
		if output == "" {
			return errorResult(fmt.Sprintf("apidiff failed: %v", err)), nil, nil
		}
		// If output is present, likely just findings.
	}

	if output == "" {
		output = "No changes found."
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: output},
		},
	}, nil, nil
}

func errorResult(msg string) *mcp.CallToolResult {
	return &mcp.CallToolResult{
		IsError: true,
		Content: []mcp.Content{
			&mcp.TextContent{Text: msg},
		},
	}
}

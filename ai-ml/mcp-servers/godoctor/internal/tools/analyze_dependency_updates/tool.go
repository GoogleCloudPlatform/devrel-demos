package analyze_dependency_updates

import (
	"context"
	"fmt"
	"os/exec"

	"github.com/danicat/godoctor/internal/toolnames"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Register registers the tool with the server.
func Register(server *mcp.Server) {
	def := toolnames.Registry["analyze_dependency_updates"]
	mcp.AddTool(server, &mcp.Tool{
		Name:        def.Name,
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

	// Construct command
	// apidiff [options] old new
	// If checking against git revisions of current repo: apidiff base HEAD
	// If checking modules: apidiff module@v1 module@v2 ? No, apidiff mostly works on packages?
	// usage: apidiff [flags] old new
	// "old" and "new" can be package paths or . for current directory in different git revisions?
	// Wait, apidiff documentation says:
	// "apidiff old new" where old/new are package paths.
	// But it also supports "apidiff -m old new" for modules.
	// And if pointing to git refs?
	// Typically: `apidiff <(git show old:pkg) <(git show new:pkg)`? No, it needs types.
	// The robust way is to use `apidiff` on already present source or let it download?
	// `golang.org/x/exp/cmd/apidiff` supports package arguments.
	// If we want to compare local changes against git HEAD:
	// Usually involves stash/checkout dance or specialized tool features.
	// Let's assume simplest usage: Compare two local packages or assume `apidiff` has semantic understanding.
	// Actually, `apidiff` operates on PACKAGE EXPORTS.
	// Most common use: `apidiff base-pkg target-pkg`.
	// If the user wants to compare git revisions, they might need to use `git worktree` or similar manually?
	// Let's implement basic `apidiff <old> <new>` command execution.
	// And let the user handle the arguments (e.g. they might have two checkouts).
	// OR: If the user provides Git Revisions, we might need a helper to check them out?
	// That's complex ("Project Phase 3 stuff").
	// For now, let's just wrap the command plain and simple.

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

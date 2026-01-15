package rename_symbol

import (
	"context"
	"fmt"
	"os/exec"

	"github.com/danicat/godoctor/internal/toolnames"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Register registers the tool with the server.
func Register(server *mcp.Server) {
	def := toolnames.Registry["rename_symbol"]
	mcp.AddTool(server, &mcp.Tool{
		Name:        def.Name,
		Title:       def.Title,
		Description: def.Description,
	}, toolHandler)
}

// Params defines the input parameters.
type Params struct {
	File    string `json:"file" jsonschema:"File containing the identifier to rename"`
	Line    int    `json:"line" jsonschema:"Line number (1-based)"`
	Col     int    `json:"col" jsonschema:"Column number (1-based)"`
	NewName string `json:"new_name" jsonschema:"The new name for the identifier"`
}

func toolHandler(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	// Check for gopls
	if _, err := exec.LookPath("gopls"); err != nil {
		return errorResult("Tool 'gopls' not found. Please install: go install golang.org/x/tools/gopls@latest"), nil, nil
	}

	if args.File == "" || args.NewName == "" || args.Line < 1 || args.Col < 1 {
		return errorResult("Invalid arguments: file, new_name, line (>0), and col (>0) are required"), nil, nil
	}

	// Position format: file:line:col
	// Note: gopls uses byte offsets optionally, but line:col is user-friendly.
	// However, gopls rename command signature:
	// gopls rename [flags] <location> <newname>
	// location is file:line:col-offset? Or file:line:col?
	// Let's assume file:line:col

	location := fmt.Sprintf("%s:%d:%d", args.File, args.Line, args.Col)

	// Command: gopls rename -w <location> <newname>
	// -w writes changes.

	cmd := exec.CommandContext(ctx, "gopls", "rename", "-w", location, args.NewName)
	// We might need to run in module root?
	// gopls usually finds the module based on file path.

	out, err := cmd.CombinedOutput()
	output := string(out)

	if err != nil {
		return errorResult(fmt.Sprintf("gopls rename failed: %v\nOutput: %s", err, output)), nil, nil
	}

	if output == "" {
		output = fmt.Sprintf("Successfully renamed symbol at %s to %s", location, args.NewName)
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

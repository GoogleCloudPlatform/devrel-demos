// Package read_code implements the code reading and symbol extraction tool.
package read

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/danicat/godoctor/internal/roots"
	"github.com/danicat/godoctor/internal/toolnames"
	"github.com/danicat/godoctor/internal/tools/shared"
	"github.com/modelcontextprotocol/go-sdk/mcp"
	"golang.org/x/tools/go/packages"
)

// Register registers the read_code tool with the server.
func Register(server *mcp.Server) {
	def := toolnames.Registry["file.read"]
	mcp.AddTool(server, &mcp.Tool{
		Name:        def.ExternalName,
		Title:       def.Title,
		Description: def.Description,
	}, readCodeHandler)
}

// Params defines the input parameters for the read_code tool.
type Params struct {
	Filename  string `json:"filename" jsonschema:"The path to the file to read"`
	StartLine int    `json:"start_line,omitempty" jsonschema:"Optional: start reading from this line number"`
	EndLine   int    `json:"end_line,omitempty" jsonschema:"Optional: stop reading at this line number"`
}

func readCodeHandler(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	absPath, err := roots.Global.Validate(args.Filename)
	if err != nil {
		return errorResult(err.Error()), nil, nil
	}

	//nolint:gosec // G304: File path provided by user is validated against roots.
	content, err := os.ReadFile(absPath)
	args.Filename = absPath // ensure we use absolute path for analysis

	if err != nil {
		return errorResult(fmt.Sprintf("failed to read file: %v", err)), nil, nil
	}

	var diags []string
	isGo := strings.HasSuffix(args.Filename, ".go")
	original := string(content)

	// 1. Partial Read & Line Numbering
	startLine := args.StartLine
	if startLine <= 0 {
		startLine = 1
	}
	endLine := args.EndLine

	startOffset, endOffset, err := shared.GetLineOffsets(original, startLine, endLine)
	if err != nil {
		return errorResult(fmt.Sprintf("line range error: %v", err)), nil, nil
	}

	viewContent := original[startOffset:endOffset]
	lines := strings.Split(viewContent, "\n")
	
	// Remove trailing empty line from split if it exists and wasn't intended
	if len(lines) > 0 && lines[len(lines)-1] == "" && !strings.HasSuffix(viewContent, "\n") {
		lines = lines[:len(lines)-1]
	}

	var contentWithLines strings.Builder
	for i, line := range lines {
		contentWithLines.WriteString(fmt.Sprintf("%4d | %s\n", startLine+i, line))
	}

	isPartial := args.StartLine > 1 || args.EndLine > 0

	if isGo && !isPartial {
		// 2. Static Analysis (Compilation Check) - Only for full read
		diags, _ = checkAnalysis(ctx, args.Filename)
	}

	// 3. Output Formatting
	var sb strings.Builder
	rangeInfo := ""
	if isPartial {
		rangeInfo = fmt.Sprintf(" (Lines %d-%d)", startLine, startLine+len(lines)-1)
	}
	sb.WriteString(fmt.Sprintf("# File: %s%s\n\n", args.Filename, rangeInfo))

	sb.WriteString("```")
	if isGo {
		sb.WriteString("go")
	}
	sb.WriteString("\n")
	sb.WriteString(contentWithLines.String())
	sb.WriteString("```\n\n")

	if isPartial {
		sb.WriteString("*Note: Partial read - analysis skipped.*\n\n")
	}

	if len(diags) > 0 {
		sb.WriteString("## Analysis (Problems)\n")
		for _, d := range diags {
			sb.WriteString(fmt.Sprintf("- ⚠️ %s\n", d))
		}
		sb.WriteString("\n")
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: sb.String()},
		},
	}, nil, nil

}

func checkAnalysis(ctx context.Context, filePath string) ([]string, error) {
	// Load the package containing the file
	cfg := &packages.Config{
		Context: ctx,
		Mode:    packages.NeedTypes | packages.NeedSyntax | packages.NeedTypesInfo,
		Dir:     filepath.Dir(filePath),
	}

	pkgs, err := packages.Load(cfg, ".")
	if err != nil {
		return nil, err
	}

	var diags []string
	seen := make(map[string]bool)

	for _, pkg := range pkgs {
		for _, err := range pkg.Errors {
			// Basic deduplication
			if !seen[err.Msg] {
				diags = append(diags, err.Msg) // err.Msg typically includes position
				seen[err.Msg] = true
			}
		}
	}

	// Limit warnings
	if len(diags) > 10 {
		diags = append(diags[:10], "... (more)")
	}

	return diags, nil
}

func errorResult(msg string) *mcp.CallToolResult {
	return &mcp.CallToolResult{
		IsError: true,
		Content: []mcp.Content{
			&mcp.TextContent{Text: msg},
		},
	}
}

// Package read_code implements the code reading and symbol extraction tool.
package read

import (
	"context"
	"fmt"
	"go/parser"
	"go/token"
	"os"
	"strings"

	"github.com/danicat/godoctor/internal/godoc"
	"github.com/danicat/godoctor/internal/roots"
	"github.com/danicat/godoctor/internal/toolnames"
	"github.com/danicat/godoctor/internal/tools/file/outline"
	"github.com/danicat/godoctor/internal/tools/shared"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Register registers the read_code tool with the server.
func Register(server *mcp.Server) {
	def := toolnames.Registry["smart_read"] // Using new name mapping
	mcp.AddTool(server, &mcp.Tool{
		Name:        def.Name,
		Title:       def.Title,
		Description: def.Description,
	}, readCodeHandler)
}

// Params defines the input parameters for the read_code tool.
type Params struct {
	Filename  string `json:"filename" jsonschema:"The path to the file to read"`
	Outline   bool   `json:"outline,omitempty" jsonschema:"Optional: if true, returns the structure (AST) only"`
	StartLine int    `json:"start_line,omitempty" jsonschema:"Optional: start reading from this line number"`
	EndLine   int    `json:"end_line,omitempty" jsonschema:"Optional: stop reading at this line number"`
}

func readCodeHandler(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	absPath, err := roots.Global.Validate(args.Filename)
	if err != nil {
		return errorResult(err.Error()), nil, nil
	}
	args.Filename = absPath

	// 0. Outline Mode (if requested and no line range specified)
	if args.Outline && args.StartLine == 0 {
		out, imports, errs, err := outline.GetOutline(absPath)
		if err != nil {
			return errorResult(fmt.Sprintf("failed to generate outline: %v", err)), nil, nil
		}
		var sb strings.Builder
		sb.WriteString(fmt.Sprintf("# File: %s (Outline)\n\n", absPath))
		if len(errs) > 0 {
			sb.WriteString("## Analysis (Problems)\n")
			for _, e := range errs {
				sb.WriteString(fmt.Sprintf("- ⚠️ %v\n", e))
			}
			sb.WriteString("\n")
		}
		sb.WriteString("```go\n")
		sb.WriteString(out)
		sb.WriteString("\n```\n")

		if len(imports) > 0 {
			sb.WriteString("\n## Imports\n")
			for _, imp := range imports {
				sb.WriteString(fmt.Sprintf("- %s\n", imp))
			}
		}

		return &mcp.CallToolResult{
			Content: []mcp.Content{
				&mcp.TextContent{Text: sb.String()},
			},
		}, nil, nil
	}

	// 1. Read Content
	//nolint:gosec // G304: File path provided by user is validated against roots.
	content, err := os.ReadFile(absPath)
	if err != nil {
		return errorResult(fmt.Sprintf("failed to read file: %v", err)), nil, nil
	}

	var diags []string
	var packageDocs []string
	isGo := strings.HasSuffix(args.Filename, ".go")
	original := string(content)

	// 2. Partial Read & Line Numbering
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
	if len(lines) > 0 && lines[len(lines)-1] == "" && !strings.HasSuffix(viewContent, "\n") {
		lines = lines[:len(lines)-1]
	}

	var contentWithLines strings.Builder
	for i, line := range lines {
		contentWithLines.WriteString(fmt.Sprintf("%4d | %s\n", startLine+i, line))
	}

	isPartial := args.StartLine > 1 || args.EndLine > 0

	// 3. Light Analysis (GO ONLY)
	if isGo && !isPartial {
		fset := token.NewFileSet()
		f, err := parser.ParseFile(fset, args.Filename, content, parser.ParseComments)
		if err != nil {
			diags = append(diags, err.Error())
		} else {
			for i, imp := range f.Imports {
				if i >= 10 {
					packageDocs = append(packageDocs, "... (more imports)")
					break
				}
				pkgPath := strings.Trim(imp.Path.Value, "\"")

				// Skip standard library packages (heuristically: no dot in first path component)
				if parts := strings.Split(pkgPath, "/"); len(parts) > 0 && !strings.Contains(parts[0], ".") {
					continue
				}

				if d, err := godoc.Load(ctx, pkgPath, ""); err == nil {
					summary := strings.ReplaceAll(d.Description, "\n", " ")
					if len(summary) > 200 {
						summary = summary[:197] + "..."
					}
					packageDocs = append(packageDocs, fmt.Sprintf("- **%s**: %s", pkgPath, summary))
				}
			}
		}
	}

	// 4. Output Formatting
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

	if len(packageDocs) > 0 {
		sb.WriteString("## Imported Packages\n")
		for _, pd := range packageDocs {
			sb.WriteString(pd + "\n")
		}
		sb.WriteString("\n")
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

func errorResult(msg string) *mcp.CallToolResult {
	return &mcp.CallToolResult{
		IsError: true,
		Content: []mcp.Content{
			&mcp.TextContent{Text: msg},
		},
	}
}
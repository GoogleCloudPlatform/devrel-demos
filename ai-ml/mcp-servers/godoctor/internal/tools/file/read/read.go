// Package read_code implements the code reading and symbol extraction tool.
package read

import (
	"context"
	"fmt"
	"go/ast"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/danicat/godoctor/internal/godoc"
	"github.com/danicat/godoctor/internal/roots"
	"github.com/danicat/godoctor/internal/toolnames"
	"github.com/danicat/godoctor/internal/tools/shared"
	"github.com/modelcontextprotocol/go-sdk/mcp"
	"golang.org/x/tools/go/packages"
)

// Register registers the read_code tool with the server.
func Register(server *mcp.Server) {
	def := toolnames.Registry["file_read"]
	mcp.AddTool(server, &mcp.Tool{
		Name:        def.Name,
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
	var externals []string
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
		// 2. Static Analysis (Compilation Check & Externals) - Only for full read
		diags, externals, _ = runAnalysis(ctx, args.Filename)
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

	if len(externals) > 0 {
		sb.WriteString("## Referenced Symbols\n")
		// Limit to top 20 to avoid noise?
		count := 0
		for _, ext := range externals {
			sb.WriteString(fmt.Sprintf("%s\n", ext))
			count++
			if count >= 20 {
				sb.WriteString(fmt.Sprintf("- ... (%d more)\n", len(externals)-20))
				break
			}
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

func runAnalysis(ctx context.Context, filePath string) ([]string, []string, error) {
	// Load the package containing the file
	cfg := &packages.Config{
		Context: ctx,
		Mode:    packages.NeedTypes | packages.NeedSyntax | packages.NeedTypesInfo | packages.NeedName | packages.NeedImports | packages.NeedFiles | packages.NeedDeps,
		Dir:     filepath.Dir(filePath),
	}

	pkgs, err := packages.Load(cfg, ".")
	if err != nil {
		return nil, nil, err
	}

	var diags []string
	seenDiag := make(map[string]bool)
	var currentPkg *packages.Package

	// Collect diagnostics and find the relevant package
	for _, pkg := range pkgs {
		// Prioritize the non-test package for analysis, or the one containing the file
		for _, f := range pkg.GoFiles {
			if f == filePath {
				currentPkg = pkg
				break
			}
		}

		for _, err := range pkg.Errors {
			if !seenDiag[err.Msg] {
				diags = append(diags, err.Msg)
				seenDiag[err.Msg] = true
			}
		}
	}

	// Limit warnings
	if len(diags) > 10 {
		diags = append(diags[:10], "... (more)")
	}

	if currentPkg == nil || currentPkg.TypesInfo == nil {
		return diags, nil, nil
	}

	// Map import paths to packages for doc lookup
	pkgMap := make(map[string]*packages.Package)
	var mapPkgs func(*packages.Package)
	mapPkgs = func(p *packages.Package) {
		if _, ok := pkgMap[p.PkgPath]; ok {
			return
		}
		pkgMap[p.PkgPath] = p
		for _, imp := range p.Imports {
			mapPkgs(imp)
		}
	}
	mapPkgs(currentPkg)

	// External Type Resolution
	externalMap := make(map[string]string) // Key: "Pkg.Symbol", Value: "Signature\nDoc"
	
	// Find the AST file for this specific file
	var fileAst *ast.File
	for i, f := range currentPkg.GoFiles {
		if f == filePath {
			fileAst = currentPkg.Syntax[i]
			break
		}
	}

	if fileAst == nil {
		return diags, nil, nil
	}

	ast.Inspect(fileAst, func(n ast.Node) bool {
		ident, ok := n.(*ast.Ident)
		if !ok {
			return true
		}

		obj := currentPkg.TypesInfo.Uses[ident]
		if obj == nil || obj.Pkg() == nil {
			return true
		}

		// Filter out local symbols
		if obj.Pkg() == currentPkg.Types {
			return true
		}

		// Key format: "pkg.Name"
		key := fmt.Sprintf("%s.%s", obj.Pkg().Name(), obj.Name())
		
		// Deduplicate early
		if _, exists := externalMap[key]; exists {
			return true
		}

		// Signature
		sig := obj.Type().String()
		
		        // Docstring extraction using godoc (Source of Truth)
		        var docSummary string
		        if pkg, ok := pkgMap[obj.Pkg().Path()]; ok {
		            // Extract doc from already loaded package
		            if d, err := godoc.Extract(pkg, obj.Name()); err == nil {
		                docSummary = d.Description
		            }
		        }
		entry := fmt.Sprintf("`%s`", sig)
		if docSummary != "" {
			entry += fmt.Sprintf("\n  > %s", strings.ReplaceAll(docSummary, "\n", " "))
		}
		
		externalMap[key] = entry
		return true
	})

	var externals []string
	for k, v := range externalMap {
		// Format: `pkg.Symbol`: signature...
		externals = append(externals, fmt.Sprintf("- `%s`: %s", k, v))
	}
	sort.Strings(externals)

	return diags, externals, nil
}

func errorResult(msg string) *mcp.CallToolResult {
	return &mcp.CallToolResult{
		IsError: true,
		Content: []mcp.Content{
			&mcp.TextContent{Text: msg},
		},
	}
}

// Package outline implements the file outlining tool.
package outline

import (
	"bytes"
	"context"
	"fmt"
	"go/ast"
	"go/format"
	"go/parser"
	"go/printer"
	"go/token"
	"os"
	"strings"

	"github.com/danicat/godoctor/internal/godoc"
	"github.com/danicat/godoctor/internal/graph"
	"github.com/danicat/godoctor/internal/toolnames"
	"github.com/modelcontextprotocol/go-sdk/mcp"
	"golang.org/x/tools/go/packages"
)

// Register registers the code_outline tool with the server.
func Register(server *mcp.Server) {
	def := toolnames.Registry["file_outline"]
	mcp.AddTool(server, &mcp.Tool{
		Name:        def.Name,
		Title:       def.Title,
		Description: def.Description,
	}, Handler)
}

// Params defines the input parameters.
type Params struct {
	Filename string `json:"filename" jsonschema:"Absolute path to the Go file to outline"`
}

func Handler(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	if args.Filename == "" {
		return errorResult("filename cannot be empty"), nil, nil
	}
	if !strings.HasSuffix(args.Filename, ".go") {
		return errorResult("filename must be a Go file (*.go)"), nil, nil
	}

	outline, imports, errs, err := GetOutline(args.Filename)
	if err != nil {
		return errorResult(fmt.Sprintf("failed to generate outline: %v", err)), nil, nil
	}

	// Build Markdown Response
	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("# File: %s\n\n", args.Filename))

	if len(errs) > 0 {
		sb.WriteString("## Analysis (Problems)\n")
		for _, e := range errs {
			sb.WriteString(fmt.Sprintf("- ⚠️ %s\n", e.Msg))
		}
		sb.WriteString("\n")
	}

	sb.WriteString("## Outline\n")
	sb.WriteString("```go\n")
	sb.WriteString(outline)
	sb.WriteString("\n```\n\n")

	// Appendix: External Imports
	if len(imports) > 0 {
		sb.WriteString("## Appendix: External Imports\n")

		for _, imp := range imports {
			// Clean quotes
			pkgPath := strings.Trim(imp, "\"")

			// Skip standard lib for brevity? Spec says "external imports".
			// Standard lib usually has no dot (except "net/http", "archive/zip").
			// Heuristic: if no dot in first segment, it's std (usually).
			// Example: "fmt", "net/http" (dot in path but not domain).
			// "github.com/..." has domain.

			// Let's rely on godoc resolution.
			// We only want to burn tokens on non-std or meaningful deps.
			// Let's show all for now but minimal summary.

			doc, err := godoc.Load(ctx, pkgPath, "")

			if err == nil && doc != nil {
				sb.WriteString(fmt.Sprintf("### %s\n", pkgPath))
				sb.WriteString(doc.Description + "\n\n")

				// List top 5 funcs as a hint
				limit := 5
				if len(doc.Funcs) > 0 {
					sb.WriteString("**Exported Functions (Top 5):**\n```go\n")
					count := 0
					for _, f := range doc.Funcs {
						if count >= limit {
							break
						}
						// Extract signature only? f contains full text.
						// Just print first line of f?
						lines := strings.Split(f, "\n")
						if len(lines) > 0 {
							sb.WriteString(lines[0] + "\n")
						}
						count++
					}
					sb.WriteString("```\n")
				}
				sb.WriteString("\n")
			}
		}
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: sb.String()},
		},
	}, nil, nil
}

// GetOutline loads a file and returns its outline, list of imports, and build errors.
func GetOutline(file string) (string, []string, []packages.Error, error) {
	// 1. Load into Knowledge Graph
	pkg, err := graph.Global.Load(file)
	if err != nil {
		return "", nil, nil, fmt.Errorf("failed to load package context: %w", err)
	}

	// 2. Find the specific file
	var targetFile *ast.File
	var fset *token.FileSet
	for _, f := range pkg.Syntax {
		if pkg.Fset.File(f.Pos()).Name() == file {
			targetFile = f
			fset = pkg.Fset
			break
		}
	}

	if targetFile == nil {
		//nolint:gosec // G304: File path provided by user is expected.
		content, err := os.ReadFile(file)
		if err != nil {
			return "", nil, nil, fmt.Errorf("failed to read file: %w", err)
		}
		fset = token.NewFileSet()
		targetFile, err = parser.ParseFile(fset, file, content, parser.ParseComments)
		if err != nil {
			return "", nil, nil, fmt.Errorf("failed to parse file: %w", err)
		}
	}

	// 3. Extract imports
	var imports []string
	for _, imp := range targetFile.Imports {
		if imp.Path != nil {
			imports = append(imports, imp.Path.Value)
		}
	}

	// 4. Create Outline
	outline := outlinize(targetFile)

	// 5. Format Output
	var buf bytes.Buffer
	config := &printer.Config{Mode: printer.TabIndent | printer.UseSpaces, Tabwidth: 8}
	if err := config.Fprint(&buf, fset, outline); err != nil {
		return "", nil, nil, fmt.Errorf("failed to format outline: %w", err)
	}

	formatted, err := format.Source(buf.Bytes())
	if err != nil {
		formatted = buf.Bytes()
	}

	return string(formatted), imports, pkg.Errors, nil
}

func outlinize(f *ast.File) *ast.File {
	res := *f
	res.Decls = make([]ast.Decl, len(f.Decls))

	allowedComments := make(map[*ast.CommentGroup]bool)
	if f.Doc != nil {
		allowedComments[f.Doc] = true
	}
	for _, cg := range f.Comments {
		if cg.End() < f.Package {
			allowedComments[cg] = true
		}
	}

	for i, decl := range f.Decls {
		switch fn := decl.(type) {
		case *ast.FuncDecl:
			newFn := *fn
			newFn.Body = nil
			res.Decls[i] = &newFn
			if fn.Doc != nil {
				allowedComments[fn.Doc] = true
			}
		case *ast.GenDecl:
			res.Decls[i] = decl
			if fn.Doc != nil {
				allowedComments[fn.Doc] = true
			}
			for _, spec := range fn.Specs {
				switch s := spec.(type) {
				case *ast.TypeSpec:
					if s.Doc != nil {
						allowedComments[s.Doc] = true
					}
				case *ast.ValueSpec:
					if s.Doc != nil {
						allowedComments[s.Doc] = true
					}
				}
			}
		default:
			res.Decls[i] = decl
		}
	}

	var newComments []*ast.CommentGroup
	for _, cg := range f.Comments {
		if allowedComments[cg] {
			newComments = append(newComments, cg)
		}
	}
	res.Comments = newComments

	return &res
}

func errorResult(msg string) *mcp.CallToolResult {
	return &mcp.CallToolResult{
		IsError: true,
		Content: []mcp.Content{
			&mcp.TextContent{Text: msg},
		},
	}
}

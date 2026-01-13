package open

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

	"github.com/danicat/godoctor/internal/graph"
	"github.com/modelcontextprotocol/go-sdk/mcp"
	"golang.org/x/tools/go/packages"
)

// Register registers the open tool with the server.
func Register(server *mcp.Server) {
	mcp.AddTool(server, &mcp.Tool{
		Name:        "open",
		Title:       "Open Go File (Skeleton View)",
		Description: "Entry Point. Returns a lightweight skeleton of a Go file (imports and signatures only). Use this for 'Satellite View' exploration to save tokens and avoid context noise compared to reading the full file.",
	}, toolHandler)
}

// Params defines the input parameters for the open tool.
type Params struct {
	File string `json:"file" jsonschema:"The path to the .go file to read"`
}

func toolHandler(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	if args.File == "" {
		return errorResult("file cannot be empty"), nil, nil
	}
	if !strings.HasSuffix(args.File, ".go") {
		return errorResult("file must be a Go file (*.go)"), nil, nil
	}

	skeleton, errs, err := GetSkeleton(args.File)

	if err != nil {
		return errorResult(fmt.Sprintf("failed to generate skeleton: %v", err)), nil, nil
	}

	// 5. Build Markdown Response
	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("# File: %s\n\n", args.File))

	if len(errs) > 0 {
		sb.WriteString("## Analysis (Problems)\n")
		for _, e := range errs {
			sb.WriteString(fmt.Sprintf("- ⚠️ %s\n", e.Msg))
		}
		sb.WriteString("\n")
	}

	sb.WriteString("## Skeleton\n")
	sb.WriteString("```go\n")
	sb.WriteString(skeleton)
	sb.WriteString("\n```")

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: sb.String()},
		},
	}, nil, nil
}

// GetSkeleton loads a file and returns its skeleton (signatures only) and any build errors.
func GetSkeleton(file string) (string, []packages.Error, error) {
	// 1. Load into Knowledge Graph
	pkg, err := graph.Global.Load(file)
	if err != nil {
		return "", nil, fmt.Errorf("failed to load package context: %w", err)
	}

	// 2. Find the specific file in the loaded package
	var targetFile *ast.File
	var fset *token.FileSet
	for _, f := range pkg.Syntax {
		if pkg.Fset.File(f.Pos()).Name() == file {
			targetFile = f
			fset = pkg.Fset
			break
		}
	}

	// If not found in syntax (maybe absolute/relative path mismatch), read and parse it manually
	if targetFile == nil {
		content, err := os.ReadFile(file)
		if err != nil {
			return "", nil, fmt.Errorf("failed to read file: %w", err)
		}
		fset = token.NewFileSet()
		targetFile, err = parser.ParseFile(fset, file, content, parser.ParseComments)
		if err != nil {
			return "", nil, fmt.Errorf("failed to parse file: %w", err)
		}
	}

	// 3. Create Skeleton (clone to avoid modifying original in graph)
	skeleton := skeletonize(targetFile)

	// 4. Format Output
	var buf bytes.Buffer
	config := &printer.Config{Mode: printer.TabIndent | printer.UseSpaces, Tabwidth: 8}
	if err := config.Fprint(&buf, fset, skeleton); err != nil {
		return "", nil, fmt.Errorf("failed to format skeleton: %w", err)
	}

	// Optional: final gofmt pass for safety
	formatted, err := format.Source(buf.Bytes())
	if err != nil {
		// Fallback to unformatted if gofmt fails for some reason
		formatted = buf.Bytes()
	}

	return string(formatted), pkg.Errors, nil
}

func skeletonize(f *ast.File) *ast.File {
	// Shallow copy of the file to preserve metadata
	res := *f
	res.Decls = make([]ast.Decl, len(f.Decls))

	// Map to keep track of allowed comments
	allowedComments := make(map[*ast.CommentGroup]bool)
	if f.Doc != nil {
		allowedComments[f.Doc] = true
	}

	// Keep comments before the package declaration (e.g. license headers)
	for _, cg := range f.Comments {
		if cg.End() < f.Package {
			allowedComments[cg] = true
		}
	}

	for i, decl := range f.Decls {
		switch fn := decl.(type) {
		case *ast.FuncDecl:
			// Clone the function decl and remove its body
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

	// Filter comments
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

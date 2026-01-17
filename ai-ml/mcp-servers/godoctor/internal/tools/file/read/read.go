// Package read_code implements the code reading and symbol extraction tool.
package read

import (
	"context"
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/danicat/godoctor/internal/roots"
	"github.com/danicat/godoctor/internal/toolnames"
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
	Filename string `json:"filename"`
}

type symbol struct {
	Name string
	Type string
	Line int
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

	if !strings.HasSuffix(args.Filename, ".go") {
		return &mcp.CallToolResult{
			Content: []mcp.Content{
				&mcp.TextContent{Text: fmt.Sprintf("# File: %s\n\n```\n%s\n```", args.Filename, string(content))},
			},
		}, nil, nil
	}

	fset := token.NewFileSet()
	file, err := parser.ParseFile(fset, args.Filename, content, parser.ParseComments)
	if err != nil {
		// If it's not a Go file or has errors, still return the content but skip symbols/analysis
		return &mcp.CallToolResult{
			Content: []mcp.Content{
				&mcp.TextContent{Text: fmt.Sprintf("# File: %s\n\n```go\n%s\n```\n\n*Note: Symbol extraction skipped due to parse error: %v*", args.Filename, string(content), err)},
			},
		}, nil, nil
	}

	// 1. Symbol Extraction
	var symbols []symbol
	ast.Inspect(file, func(n ast.Node) bool {
		switch x := n.(type) {
		case *ast.FuncDecl:
			name := x.Name.Name
			if x.Recv != nil && len(x.Recv.List) > 0 {
				recv := x.Recv.List[0].Type
				name = fmt.Sprintf("(%s) %s", typeToString(recv), name)
			}
			symbols = append(symbols, symbol{
				Name: name,
				Type: "Function",
				Line: fset.Position(x.Pos()).Line,
			})
		case *ast.TypeSpec:
			symbols = append(symbols, symbol{
				Name: x.Name.Name,
				Type: "Type",
				Line: fset.Position(x.Pos()).Line,
			})
		case *ast.ValueSpec:
			for _, name := range x.Names {
				symbols = append(symbols, symbol{
					Name: name.Name,
					Type: "Variable/Constant",
					Line: fset.Position(x.Pos()).Line,
				})
			}
		}
		return true
	})

	sort.Slice(symbols, func(i, j int) bool {
		return symbols[i].Line < symbols[j].Line
	})

	// 2. Static Analysis
	diags, _ := checkAnalysis(ctx, args.Filename) // Ignore generic error, just show diagnostics if any
	// 3. Output Formatting
	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("# File: %s\n\n", args.Filename))

	sb.WriteString("## Content\n")
	sb.WriteString("```go\n")
	sb.WriteString(string(content))
	sb.WriteString("\n```\n\n")

	if len(symbols) > 0 {
		sb.WriteString("## Symbols\n")
		for _, sym := range symbols {
			sb.WriteString(fmt.Sprintf("- `%s` (%s) at line %d\n", sym.Name, sym.Type, sym.Line))
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

func typeToString(expr ast.Expr) string {
	switch x := expr.(type) {
	case *ast.Ident:
		return x.Name
	case *ast.StarExpr:
		return "*" + typeToString(x.X)
	case *ast.SelectorExpr:
		return typeToString(x.X) + "." + x.Sel.Name
	default:
		return fmt.Sprintf("%T", expr)
	}
}

func errorResult(msg string) *mcp.CallToolResult {
	return &mcp.CallToolResult{
		IsError: true,
		Content: []mcp.Content{
			&mcp.TextContent{Text: msg},
		},
	}
}

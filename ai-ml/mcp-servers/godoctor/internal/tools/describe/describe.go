package describe

import (
	"context"
	"fmt"
	"os"
	"strings"

	"github.com/danicat/godoctor/internal/godoc"
	"github.com/danicat/godoctor/internal/graph"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Register registers the describe tool with the server.
func Register(server *mcp.Server) {
	mcp.AddTool(server, &mcp.Tool{
		Name:        "describe",
		Title:       "Describe Symbol or Package",
		Description: "The deep-dive explorer. Retrieves Ground Truth (full documentation, implementation source, and usage references) for any symbol. Use this to verify APIs before implementing code.",
	}, toolHandler)
}

// Params defines the input parameters for the describe tool.
type Params struct {
	Package string `json:"package,omitempty" jsonschema:"The import path of the package (e.g. 'fmt')"`
	Symbol  string `json:"symbol,omitempty" jsonschema:"The name of the symbol to look up"`
	File    string `json:"file,omitempty" jsonschema:"A local file path to resolve context from"`
}

func toolHandler(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	if args.Package == "" && args.File == "" {
		return errorResult("at least package or file must be specified"), nil, nil
	}
	if args.File != "" && !strings.HasSuffix(args.File, ".go") {
		return errorResult("file must be a Go file (*.go)"), nil, nil
	}

	desc, err := Describe(ctx, args.Package, args.Symbol, args.File)

	if err != nil {
		return errorResult(err.Error()), nil, nil
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: desc},
		},
	}, nil, nil
}

// Describe resolves the documentation/source for a symbol.
func Describe(ctx context.Context, pkgName, symName, fileName string) (string, error) {
	// 1. Try Graph Resolution (Source Code aware)
	// We attempt this for ALL packages now, as we want to provide source code if possible.
	localResult := resolveLocal(pkgName, symName, fileName)
	if localResult != "" {
		return localResult, nil
	}

	// 2. Try External Resolution (Godoc) - Fallback for when source isn't available
	if pkgName != "" {
		markdown, err := godoc.GetDocumentation(ctx, pkgName, symName)
		if err == nil {
			return markdown, nil
		}
	}

	return "", fmt.Errorf("could not find description for symbol %q in %s", symName, pkgName)
}

func resolveLocal(pkgName, symName, fileName string) string {
	target := fileName
	if target == "" {
		target = pkgName
	}

	pkg, err := graph.Global.Load(target)
	if err != nil {
		return ""
	}

	if symName == "" {
		// Return full file content if File is specified, else package overview
		if fileName != "" {
			content, _ := os.ReadFile(fileName)
			return fmt.Sprintf("# File: %s\n\n```go\n%s\n```", fileName, string(content))
		}
		return fmt.Sprintf("# Package: %s\n\n%s", pkg.Name, "Local package loaded.")
	}

	obj := graph.Global.FindObject(pkg, symName)
	if obj == nil {
		return ""
	}

	source, file, line := graph.Global.FindSymbolLocation(pkg, obj)
	refs := graph.Global.FindReferences(obj)

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("# Symbol: %s\n", symName))
	sb.WriteString(fmt.Sprintf("Defined in: `%s:%d`\n\n", file, line))

	if source != "" {
		sb.WriteString("## Implementation\n")
		sb.WriteString("```go\n")
		sb.WriteString(source)
		sb.WriteString("\n```\n\n")
	}

	if len(refs) > 0 {
		sb.WriteString("## Usages\n")
		for _, ref := range refs {
			sb.WriteString(fmt.Sprintf("- `%s:%d`\n", ref.File, ref.Line))
		}
		sb.WriteString("\n")
	}
	related := graph.Global.FindRelatedSymbols(obj)
	if len(related) > 0 {
		sb.WriteString("## Definitions\n")
		for _, rel := range related {
			if rel.Pkg() == nil {
				continue // Skip builtins
			}

			// We need to find the package that contains this symbol.
			// Ideally rel.Pkg().Path() gives us the import path.
			// We can try to get it from the graph.
			relPkg := graph.Global.Get(rel.Pkg().Path())
			if relPkg == nil {
				// Try to load it if not found
				var err error
				relPkg, err = graph.Global.Load(rel.Pkg().Path())
				if err != nil {
					continue
				}
			}

			if relPkg != nil {
				src, file, line := graph.Global.FindSymbolLocation(relPkg, rel)
				if src != "" {
					sb.WriteString(fmt.Sprintf("### %s\n", rel.Name()))
					sb.WriteString(fmt.Sprintf("Defined in: `%s:%d`\n", file, line))
					sb.WriteString("```go\n")
					sb.WriteString(src)
					sb.WriteString("\n```\n\n")
				}
			}
		}
	}

	return sb.String()
}

func errorResult(msg string) *mcp.CallToolResult {
	return &mcp.CallToolResult{
		IsError: true,
		Content: []mcp.Content{
			&mcp.TextContent{Text: msg},
		},
	}
}

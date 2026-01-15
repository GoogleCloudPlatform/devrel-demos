package inspect

import (
	"context"
	"fmt"
	"go/types"
	"os"
	"strings"

	"github.com/danicat/godoctor/internal/godoc"
	"github.com/danicat/godoctor/internal/graph"
	"github.com/danicat/godoctor/internal/toolnames"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Register registers the inspect_symbol tool with the server.
func Register(server *mcp.Server) {
	def := toolnames.Registry["symbol.inspect"]
	mcp.AddTool(server, &mcp.Tool{
		Name:        def.ExternalName,
		Title:       def.Title,
		Description: def.Description,
	}, Handler)
}

// Params defines the input parameters.
type Params struct {
	File    string `json:"file,omitempty" jsonschema:"File context for local lookup"`
	Package string `json:"package,omitempty" jsonschema:"Package path (if not local or explicit external lookup)"`
	Symbol  string `json:"symbol" jsonschema:"Symbol name to inspect"`
}

func Handler(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
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
	localDoc := resolveLocal(ctx, pkgName, symName, fileName)
	if localDoc != nil {
		return godoc.Render(localDoc), nil
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

func resolveLocal(ctx context.Context, pkgName, symName, fileName string) *godoc.StructuredDoc {
	target := fileName
	if target == "" {
		target = pkgName
	}

	pkg, err := graph.Global.Load(target)
	if err != nil {
		return nil
	}

	doc := &godoc.StructuredDoc{
		ImportPath:  pkg.PkgPath,
		Package:     pkg.Name,
		PkgGoDevURL: fmt.Sprintf("https://pkg.go.dev/%s", pkg.PkgPath),
	}

	if symName == "" {
		// Package Overview
		if fileName != "" {
			content, _ := os.ReadFile(fileName)
			doc.Definition = fmt.Sprintf("// File: %s\n%s", fileName, string(content))
			return doc
		}

		// Enrich with sub-packages using 'go list' logic from godoc package
		// We need the directory of the package to run go list
		if len(pkg.GoFiles) > 0 {
			pkgDir := strings.TrimSuffix(pkg.GoFiles[0], "/"+strings.Split(pkg.GoFiles[0], "/")[len(strings.Split(pkg.GoFiles[0], "/"))-1])
			// Actually filepath.Dir is safer but we don't import filepath here yet
			// Let's assume graph package provides a way or we just use the first file's dir
			// But wait, pkg.GoFiles[0] is absolute path.
			// Let's use graph.Global.FindObject which requires loading...
			// simpler:
			doc.SubPackages = godoc.ListSubPackages(ctx, pkgDir) // This requires directory
		} else {
			// Fallback to graph known packages if no files (e.g. empty dir loaded)
			// But graph.Global.Load would fail if no files.
		}

		// Add public symbols to description for overview
		var sb strings.Builder
		if len(pkg.Errors) > 0 {
			sb.WriteString("## Build Problems\n")
			for _, e := range pkg.Errors {
				sb.WriteString(fmt.Sprintf("- ⚠️ %s\n", e.Msg))
			}
			sb.WriteString("\n")
		}

		if pkg.Types != nil && pkg.Types.Scope() != nil {
			sb.WriteString("## Public Symbols\n")
			names := pkg.Types.Scope().Names()
			for _, name := range names {
				obj := pkg.Types.Scope().Lookup(name)
				if obj != nil && obj.Exported() {
					sb.WriteString(fmt.Sprintf("- `%s` (%s)\n", name, formatType(obj.Type())))
				}
			}
		}
		doc.Description = sb.String()

		return doc
	}

	// Symbol Lookup
	obj := graph.Global.FindObject(pkg, symName)
	if obj == nil {
		return nil
	}

	source, file, line := graph.Global.FindSymbolLocation(pkg, obj)
	refs := graph.Global.FindReferences(obj)

	doc.SymbolName = symName
	doc.Type = "symbol" // generic, specific type not easily available from object interface without casting
	doc.SourcePath = file
	doc.Line = line
	doc.Definition = source

	// Format References
	for _, ref := range refs {
		doc.References = append(doc.References, fmt.Sprintf("`%s:%d`", ref.File, ref.Line))
	}

	// Related Symbols (Definitions)
	related := graph.Global.FindRelatedSymbols(obj)
	if len(related) > 0 {
		var sb strings.Builder
		sb.WriteString("## Related Definitions\n")
		for _, rel := range related {
			if rel.Pkg() == nil {
				continue
			}
			// Resolve related symbol location
			// We can't easily recurse here without bloating the doc, so we just list them or short snippet?
			// The original implementation printed source. Let's append to Description or Definition?
			// Let's append to Description for now as "Related Code"

			// We need to load the related package if different
			relPkg := graph.Global.Get(rel.Pkg().Path())
			if relPkg == nil {
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
		doc.Description += "\n" + sb.String()
	}

	return doc
}

func formatType(t types.Type) string {
	if t == nil {
		return "unknown"
	}
	s := t.String()
	// Clean up long package paths in signatures
	return s
}

func errorResult(msg string) *mcp.CallToolResult {
	return &mcp.CallToolResult{
		IsError: true,
		Content: []mcp.Content{
			&mcp.TextContent{Text: msg},
		},
	}
}

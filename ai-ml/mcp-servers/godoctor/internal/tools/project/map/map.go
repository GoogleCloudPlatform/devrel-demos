package projectmap

import (
	"context"
	"fmt"
	"path/filepath"
	"sort"
	"strings"

	"github.com/danicat/godoctor/internal/graph"
	"github.com/danicat/godoctor/internal/toolnames"
	"github.com/modelcontextprotocol/go-sdk/mcp"
	"golang.org/x/tools/go/packages"
)

// Register registers the tool with the server.
func Register(server *mcp.Server) {
	def := toolnames.Registry["project.map"]
	mcp.AddTool(server, &mcp.Tool{
		Name:        def.ExternalName,
		Title:       def.Title,
		Description: def.Description,
	}, Handler)
}

// Params defines the input parameters.
type Params struct {
	// No params for now, maybe 'Filter' in the future
}

func Handler(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	// Initialize graph if not done (though usually server handles this)
	if graph.Global.Root == "" {
		graph.Global.Initialize(".")
	}

	pkgs := graph.Global.ListPackages()

	// Sort for deterministic output
	sort.Slice(pkgs, func(i, j int) bool {
		return pkgs[i].PkgPath < pkgs[j].PkgPath
	})

	var localPkgs []*packages.Package
	var externalPkgs []*packages.Package

	root := graph.Global.Root

	for _, pkg := range pkgs {
		isLocal := false
		for _, f := range pkg.GoFiles {
			rel, err := filepath.Rel(root, f)
			if err == nil && !strings.HasPrefix(rel, "..") {
				isLocal = true
				break
			}
		}
		if isLocal {
			localPkgs = append(localPkgs, pkg)
		} else {
			externalPkgs = append(externalPkgs, pkg)
		}
	}

	var sb strings.Builder
	sb.WriteString("# Project Map\n\n")
	sb.WriteString(fmt.Sprintf("Indexed Packages: %d (Local: %d, External: %d)\n\n",
		len(pkgs), len(localPkgs), len(externalPkgs)))

	sb.WriteString("## 🏠 Local Packages\n\n")
	renderPackageList(&sb, localPkgs, root)

	if len(externalPkgs) > 0 {
		sb.WriteString("\n## 📦 External Dependencies & Stdlib\n\n")
		// Limit external packages to avoid token bloat
		if len(externalPkgs) > 10 { // Stricter limit for tool output
			sb.WriteString(fmt.Sprintf("<details><summary>Show %d external packages</summary>\n\n", len(externalPkgs)))
			renderPackageList(&sb, externalPkgs, "")
			sb.WriteString("\n</details>\n")
		} else {
			renderPackageList(&sb, externalPkgs, "")
		}
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: sb.String()},
		},
	}, nil, nil
}

func renderPackageList(sb *strings.Builder, pkgs []*packages.Package, root string) {
	for _, pkg := range pkgs {
		sb.WriteString(fmt.Sprintf("- **%s**\n", pkg.PkgPath))
		var files []string
		for _, f := range pkg.GoFiles {
			files = append(files, f)
		}
		sort.Strings(files)

		for _, f := range files {
			display := f
			if root != "" {
				rel, err := filepath.Rel(root, f)
				if err == nil && !strings.HasPrefix(rel, "..") {
					display = rel
				}
			}
			sb.WriteString(fmt.Sprintf("  - %s\n", display))
		}
	}
}

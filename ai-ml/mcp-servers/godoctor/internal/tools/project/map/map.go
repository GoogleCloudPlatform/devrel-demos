// Package projectmap implements the project mapping tool.
package projectmap

import (
	"context"
	"fmt"
	"path/filepath"
	"sort"
	"strings"

	"github.com/danicat/godoctor/internal/graph"
	"github.com/danicat/godoctor/internal/roots"
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
}

func Handler(ctx context.Context, req *mcp.CallToolRequest, _ Params) (*mcp.CallToolResult, any, error) {
	// Initialize graph/roots if not done
	if len(roots.Global.Get()) == 0 {
		roots.Global.Sync(ctx, req.Session)
	}

	pkgs := graph.Global.ListPackages()
	if len(pkgs) == 0 {
		_ = graph.Global.Scan()
		pkgs = graph.Global.ListPackages()
	}

	// Sort for deterministic output
	sort.Slice(pkgs, func(i, j int) bool {
		return pkgs[i].PkgPath < pkgs[j].PkgPath
	})

	var localPkgs []*packages.Package
	var externalPkgs []*packages.Package

	rts := roots.Global.Get()

	for _, pkg := range pkgs {
		isLocal := false
		for _, f := range pkg.GoFiles {
			for _, root := range rts {
				rel, err := filepath.Rel(root, f)
				if err == nil && !strings.HasPrefix(rel, "..") {
					isLocal = true
					break
				}
			}
			if isLocal {
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
	renderPackageList(&sb, localPkgs, rts)

	if len(externalPkgs) > 0 {
		sb.WriteString("\n## 📦 External Dependencies & Stdlib\n\n")
		// Limit external packages to avoid token bloat
		if len(externalPkgs) > 10 { // Stricter limit for tool output
			sb.WriteString(fmt.Sprintf("<details><summary>Show %d external packages</summary>\n\n", len(externalPkgs)))
			renderPackageList(&sb, externalPkgs, nil)
			sb.WriteString("\n</details>\n")
		} else {
			renderPackageList(&sb, externalPkgs, nil)
		}
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: sb.String()},
		},
	}, nil, nil
}

func renderPackageList(sb *strings.Builder, pkgs []*packages.Package, rts []string) {
	for _, pkg := range pkgs {
		fmt.Fprintf(sb, "- **%s**\n", pkg.PkgPath)
		files := make([]string, 0, len(pkg.GoFiles))
		files = append(files, pkg.GoFiles...)
		sort.Strings(files)

		for _, f := range files {
			display := f
			if len(rts) > 0 {
				for _, root := range rts {
					rel, err := filepath.Rel(root, f)
					if err == nil && !strings.HasPrefix(rel, "..") {
						display = rel
						break
					}
				}
			}
			fmt.Fprintf(sb, "  - %s\n", display)
		}
	}
}

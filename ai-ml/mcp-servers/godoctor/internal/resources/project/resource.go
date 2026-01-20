package project

import (
	"context"
	"fmt"
	"path/filepath"
	"sort"
	"strings"

	"github.com/danicat/godoctor/internal/graph"
	"github.com/danicat/godoctor/internal/roots"
	"github.com/modelcontextprotocol/go-sdk/mcp"
	"golang.org/x/tools/go/packages"
)

// Register registers the project resources.
func Register(server *mcp.Server) {
	server.AddResource(&mcp.Resource{
		URI:         "project://map",
		Name:        "Project Map",
		Title:       "🗺️ Project Structure Map",
		Description: "A hierarchical map of all indexed packages and files.",
		MIMEType:    "text/markdown",
	}, ResourceHandler)
}

func ResourceHandler(_ context.Context, req *mcp.ReadResourceRequest) (*mcp.ReadResourceResult, error) {
	if req.Params.URI != "project://map" {
		return nil, mcp.ResourceNotFoundError(req.Params.URI)
	}

	pkgs := graph.Global.ListPackages()

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
		if len(externalPkgs) > 20 {
			sb.WriteString(fmt.Sprintf("<details><summary>Show %d external packages</summary>\n\n", len(externalPkgs)))
			renderPackageList(&sb, externalPkgs, nil)
			sb.WriteString("\n</details>\n")
		} else {
			renderPackageList(&sb, externalPkgs, nil)
		}
	}

	return &mcp.ReadResourceResult{
		Contents: []*mcp.ResourceContents{
			{
				URI:      req.Params.URI,
				MIMEType: "text/markdown",
				Text:     sb.String(),
			},
		},
	}, nil
}

func renderPackageList(sb *strings.Builder, pkgs []*packages.Package, rts []string) {
	for _, pkg := range pkgs {
		fmt.Fprintf(sb, "- **%s**\n", pkg.PkgPath)
		files := make([]string, 0, len(pkg.GoFiles))
		files = append(files, pkg.GoFiles...)
		sort.Strings(files)

		for _, f := range files {
			display := f
			uri := "code://" + f
			if len(rts) > 0 {
				for _, root := range rts {
					rel, err := filepath.Rel(root, f)
					if err == nil && !strings.HasPrefix(rel, "..") {
						display = rel
						uri = "code://" + rel
						break
					}
				}
			}

			// Ensure triple slash for absolute paths
			if !strings.HasPrefix(uri, "code:///") && strings.HasPrefix(uri, "code://") && strings.HasPrefix(f, "/") {
				uri = "code://" + f
			}

			fmt.Fprintf(sb, "  - [%s](%s)\n", display, uri)
		}
	}
}

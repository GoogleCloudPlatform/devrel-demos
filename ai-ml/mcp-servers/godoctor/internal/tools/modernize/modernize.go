package modernize

import (
	"context"
	"fmt"
	"go/format"
	"go/token"
	"log"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/modelcontextprotocol/go-sdk/mcp"
	"golang.org/x/tools/go/analysis"
	"golang.org/x/tools/go/analysis/passes/modernize"
	"golang.org/x/tools/go/packages"
)

// Register registers the tool with the server.
func Register(server *mcp.Server) {
	mcp.AddTool(server, &mcp.Tool{
		Name:        "modernize",
		Title:       "Modernize Go Code",
		Description: "Runs the 'modernize' analyzer to suggest and apply updates for newer Go versions (e.g. replacing s[i:len(s)] with s[i:], using min/max/slices/maps packages).",
	}, toolHandler)
}

// Params defines the input parameters.
type Params struct {
	Dir string `json:"dir,omitempty" jsonschema:"Directory to run analysis in (default: current)"`
	Fix bool   `json:"fix,omitempty" jsonschema:"Whether to automatically apply the suggested fixes (default: false)"`
}

func toolHandler(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	dir := args.Dir
	if dir == "" {
		dir = "."
	}
	absDir, _ := filepath.Abs(dir)

	// Load packages
	cfg := &packages.Config{
		Mode:    packages.LoadAllSyntax,
		Dir:     absDir,
		Context: ctx,
	}
	pkgs, err := packages.Load(cfg, "./...")
	if err != nil {
		return errorResult(fmt.Sprintf("failed to load packages: %v", err)), nil, nil
	}
	if len(pkgs) == 0 {
		return errorResult("no packages found"), nil, nil
	}

	// Prepare analyzers
	analyzers := modernize.Suite

	var sb strings.Builder
	var appliedCount int
	var pendingCount int

	// Run analysis per package
	for _, pkg := range pkgs {
		if len(pkg.Errors) > 0 {
			for _, e := range pkg.Errors {
				sb.WriteString(fmt.Sprintf("❌ Package %s error: %v\n", pkg.PkgPath, e))
			}
			continue
		}

		for _, analyzer := range analyzers {
			pass := &analysis.Pass{
				Analyzer:  analyzer,
				Fset:      pkg.Fset,
				Files:     pkg.Syntax,
				Pkg:       pkg.Types,
				TypesInfo: pkg.TypesInfo,
				Report: func(d analysis.Diagnostic) {
					// Handle report
					pos := pkg.Fset.Position(d.Pos)
					file := pos.Filename
					relFile, _ := filepath.Rel(absDir, file)
					if relFile == "" {
						relFile = file
					}

					sb.WriteString(fmt.Sprintf("⚠️ [%s] %s:%d: %s\n", analyzer.Name, relFile, pos.Line, d.Message))

					if len(d.SuggestedFixes) > 0 {
						if args.Fix {
							// Apply fixes
							if err := applyFixes(pkg.Fset, d.SuggestedFixes); err != nil {
								sb.WriteString(fmt.Sprintf("   Failed to apply fix: %v\n", err))
							} else {
								sb.WriteString("   ✅ Applied fix.\n")
								appliedCount++
							}
						} else {
							pendingCount++
							sb.WriteString(fmt.Sprintf("   💡 Fix available (run with fix=true to apply)\n"))
							for _, fix := range d.SuggestedFixes {
								for _, edit := range fix.TextEdits {
									sb.WriteString(fmt.Sprintf("      - Replace at %d .. %d\n", edit.Pos, edit.End))
								}
							}
						}
					}
					sb.WriteString("\n")
				},
			}

			_, err := analyzer.Run(pass)
			if err != nil {
				sb.WriteString(fmt.Sprintf("❌ Analysis '%s' failed for %s: %v\n", analyzer.Name, pkg.PkgPath, err))
			}
		}
	}

	summary := fmt.Sprintf("\nAnalysis Complete.\nPending Fixes: %d\nApplied Fixes: %d\n", pendingCount, appliedCount)
	sb.WriteString(summary)

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: sb.String()},
		},
	}, nil, nil
}

func applyFixes(fset *token.FileSet, fixes []analysis.SuggestedFix) error {
	// Simple application of text edits.
	// We must group edits by file and apply them from back to front to avoid offset shifting issues,
	// or use a robust applier.
	// This simple implementation applies one diagnostic's fixes.

	// Flatten all edits
	type edit struct {
		file *token.File
		pos  int
		end  int
		new  []byte
	}
	var edits []edit

	for _, f := range fixes {
		for _, te := range f.TextEdits {
			file := fset.File(te.Pos)
			if file == nil {
				continue
			}
			edits = append(edits, edit{
				file: file,
				pos:  file.Offset(te.Pos),
				end:  file.Offset(te.End),
				new:  te.NewText,
			})
		}
	}

	// Sort edits by file and position (descending)
	sort.Slice(edits, func(i, j int) bool {
		if edits[i].file.Name() != edits[j].file.Name() {
			return edits[i].file.Name() < edits[j].file.Name()
		}
		return edits[i].pos > edits[j].pos // Apply back to front
	})

	// Apply
	filesToUpdate := make(map[string][]edit)
	for _, e := range edits {
		filesToUpdate[e.file.Name()] = append(filesToUpdate[e.file.Name()], e)
	}

	for path, fileEdits := range filesToUpdate {
		content, err := os.ReadFile(path)
		if err != nil {
			return err
		}

		// Edits are already reverse sorted for this file
		for _, e := range fileEdits {
			if e.pos > len(content) || e.end > len(content) {
				return fmt.Errorf("edit out of bounds")
			}
			// Splicing
			suffix := make([]byte, len(content)-e.end)
			copy(suffix, content[e.end:])
			content = append(content[:e.pos], e.new...)
			content = append(content, suffix...)
		}

		// Reformat
		formatted, err := format.Source(content)
		if err != nil {
			log.Printf("formatting failed for %s: %v", path, err)
			formatted = content
		}

		if err := os.WriteFile(path, formatted, 0644); err != nil {
			return err
		}
	}
	return nil
}

func errorResult(msg string) *mcp.CallToolResult {
	return &mcp.CallToolResult{
		IsError: true,
		Content: []mcp.Content{
			&mcp.TextContent{Text: msg},
		},
	}
}

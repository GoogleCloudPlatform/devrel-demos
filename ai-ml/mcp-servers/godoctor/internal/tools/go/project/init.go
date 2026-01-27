// Package project implements tools for managing Go projects.
package project

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/danicat/godoctor/internal/godoc"
	"github.com/danicat/godoctor/internal/toolnames"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Register registers the tool with the server.
func Register(server *mcp.Server) {
	def := toolnames.Registry["project_init"]
	mcp.AddTool(server, &mcp.Tool{
		Name:        def.Name,
		Title:       def.Title,
		Description: def.Description,
	}, Handler)
}

// Params defines the input parameters.
type Params struct {
	Path         string   `json:"path" jsonschema:"Target directory for the project"`
	ModulePath   string   `json:"module_path" jsonschema:"Go module path (e.g., github.com/user/repo)"`
	Dependencies []string `json:"dependencies,omitempty" jsonschema:"Initial dependencies to install"`
}

// Runner defines the interface for running commands.
type Runner interface {
	Run(ctx context.Context, dir, name string, args ...string) (string, error)
}

type stdRunner struct{}

func (r *stdRunner) Run(ctx context.Context, dir, name string, args ...string) (string, error) {
	cmd := exec.CommandContext(ctx, name, args...)
	cmd.Dir = dir
	out, err := cmd.CombinedOutput()
	return string(out), err
}

var CommandRunner Runner = &stdRunner{}

func Handler(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	// 1. Create Directory
	if err := os.MkdirAll(args.Path, 0755); err != nil {
		return errorResult(fmt.Sprintf("failed to create directory: %v", err)), nil, nil
	}

	absPath, err := filepath.Abs(args.Path)
	if err != nil {
		return errorResult(fmt.Sprintf("failed to get absolute path: %v", err)), nil, nil
	}

	// 2. go mod init
	// Check if go.mod already exists
	if _, err := os.Stat(filepath.Join(absPath, "go.mod")); err == nil {
		return errorResult("project already initialized (go.mod exists)"), nil, nil
	}

	if out, err := CommandRunner.Run(ctx, absPath, "go", "mod", "init", args.ModulePath); err != nil {
		return errorResult(fmt.Sprintf("failed to init module: %v\nOutput: %s", err, out)), nil, nil
	}

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("Successfully initialized Go project at `%s`\n", args.Path))
	sb.WriteString(fmt.Sprintf("- Module: `%s`\n", args.ModulePath))

	// 3. Install dependencies
	if len(args.Dependencies) > 0 {
		sb.WriteString("- Dependencies:\n")
		
		docsNeeded := make(map[string]bool)
		
		for _, dep := range args.Dependencies {
			pkgPath := strings.Split(dep, "@")[0]
			
			if out, err := CommandRunner.Run(ctx, absPath, "go", "get", dep); err != nil {
				sb.WriteString(fmt.Sprintf("  - ⚠️ Failed to get `%s`: %v\n", dep, out))
				
				// Deduplicate by guessing module root
				parts := strings.Split(pkgPath, "/")
				if len(parts) >= 3 && strings.Contains(parts[0], ".") {
					// e.g. github.com/user/repo
					root := strings.Join(parts[:3], "/")
					docsNeeded[root] = true
				} else {
					// Fallback for standard lib or short paths
					docsNeeded[pkgPath] = true
				}
			} else {
				sb.WriteString(fmt.Sprintf("  - ✅ `%s` installed\n", dep))
				docsNeeded[pkgPath] = true
			}
		}
		// Final tidy
		CommandRunner.Run(ctx, absPath, "go", "mod", "tidy")

		// Process docs (deduplicated)
		for pkgPath := range docsNeeded {
			if docContent := godoc.GetDocumentationWithFallback(ctx, pkgPath); docContent != "" {
				sb.WriteString("\n")
				sb.WriteString(docContent)
			}
		}
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: sb.String()},
		},
	}, nil, nil
}

func errorResult(msg string) *mcp.CallToolResult {
	return &mcp.CallToolResult{
		IsError: true,
		Content: []mcp.Content{
			&mcp.TextContent{Text: msg},
		},
	}
}

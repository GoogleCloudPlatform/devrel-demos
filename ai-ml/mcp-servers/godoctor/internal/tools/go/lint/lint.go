// Package lint implements the golangci-lint tool.
package lint

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"

	"github.com/danicat/godoctor/internal/toolnames"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Register registers the tool with the server.
func Register(server *mcp.Server) {
	def := toolnames.Registry["go.lint"]
	mcp.AddTool(server, &mcp.Tool{
		Name:        def.ExternalName,
		Title:       def.Title,
		Description: def.Description,
	}, Handler)
}

// Params defines the input parameters.
type Params struct {
	Dir  string   `json:"dir,omitempty" jsonschema:"Directory to run analysis in (default: current)"`
	Args []string `json:"args,omitempty" jsonschema:"Additional arguments (e.g. ./..., --fix). Default: run ./..."`
}

const defaultConfig = `version: "2"

run:
  concurrency: 4
  timeout: 5m
  issues-exit-code: 1
  tests: true

linters:
  disable-all: true
  enable:
    - errcheck
    - govet
    - ineffassign
    - staticcheck
    - unused
    - revive
    - whitespace
    - misspell
    - gosec
`

func Handler(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	dir := args.Dir
	if dir == "" {
		dir = "."
	}

	// Check if .golangci.yml exists
	configPath := filepath.Join(dir, ".golangci.yml")
	if _, err := os.Stat(configPath); os.IsNotExist(err) {
		//nolint:gosec // G306: Creating default config with standard permissions.
		if err := os.WriteFile(configPath, []byte(defaultConfig), 0644); err != nil {
			return &mcp.CallToolResult{
				IsError: true,
				Content: []mcp.Content{
					&mcp.TextContent{Text: fmt.Sprintf("Failed to create default .golangci.yml: %v", err)},
				},
			}, nil, nil
		}
	}

	// 1. Check if installed
	_, err := exec.LookPath("golangci-lint")
	var installLog string
	if err != nil {
		// Not found, try to install
		installLog = "golangci-lint not found. Installing via 'go install github.com/golangci/golangci-lint/v2/cmd/golangci-lint@latest'...\n"

		installCmd := exec.CommandContext(ctx, "go", "install", "github.com/golangci/golangci-lint/v2/cmd/golangci-lint@latest")
		// Install usually goes to GOPATH/bin which might be in PATH, or might not.
		// If it wasn't found in LookPath, it might be because GOPATH/bin isn't in PATH.
		// However, we can try running it anyway after install, or try resolving it again.

		out, installErr := installCmd.CombinedOutput()
		if installErr != nil {
			return &mcp.CallToolResult{
				IsError: true,
				Content: []mcp.Content{
					&mcp.TextContent{Text: fmt.Sprintf("%sFailed to install golangci-lint: %v\nOutput:\n%s", installLog, installErr, out)},
				},
			}, nil, nil
		}
		installLog += "Installation successful.\n"
	}

	// 2. Prepare Command
	// We use "golangci-lint" directly. If it was just installed to $GOPATH/bin and that's not in $PATH,
	// checking LookPath again might fail.
	// A safer bet might be $(go env GOPATH)/bin/golangci-lint, but let's try the simple way first.
	// If the user's environment is set up for Go dev, GOPATH/bin should be in PATH.

	cmdArgs := []string{"run"}
	if len(args.Args) > 0 {
		cmdArgs = append(cmdArgs, args.Args...)
	} else {
		cmdArgs = append(cmdArgs, "./...")
	}

	cmd := exec.CommandContext(ctx, "golangci-lint", cmdArgs...)
	cmd.Dir = dir

	out, err := cmd.CombinedOutput()
	output := string(out)

	// golangci-lint returns non-zero exit code if issues found
	header := installLog
	if err != nil {
		// Distinguish between execution error and lint issues
		// Usually lint issues are printed to stdout/stderr
		if output == "" {
			return &mcp.CallToolResult{
				IsError: true,
				Content: []mcp.Content{
					&mcp.TextContent{Text: fmt.Sprintf("%sFailed to run golangci-lint: %v", header, err)},
				},
			}, nil, nil
		}
		header += fmt.Sprintf("Linting finished with issues (Exit Code: %v):\n", err)
	} else {
		if output == "" {
			output = "No issues found."
		}
		header += "Linting passed.\n"
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: header + output},
		},
	}, nil, nil
}

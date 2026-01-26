// Package quality implements the smart_build tool.
package quality

import (
	"context"
	"fmt"
	"os/exec"
	"strings"

	"github.com/danicat/godoctor/internal/toolnames"
	"github.com/danicat/godoctor/internal/tools/shared"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Register registers the tool with the server.
func Register(server *mcp.Server) {
	def := toolnames.Registry["smart_build"]
	mcp.AddTool(server, &mcp.Tool{
		Name:        def.Name,
		Title:       def.Title,
		Description: def.Description,
	}, Handler)
}

// Params defines the input parameters.
type Params struct {
	Dir      string `json:"dir,omitempty" jsonschema:"Directory to build in (default: current)"`
	Packages string `json:"packages,omitempty" jsonschema:"Packages to build (default: ./...)"`
	RunTests *bool  `json:"run_tests,omitempty" jsonschema:"Run unit tests after build (default: true)"`
	RunLint  *bool  `json:"run_lint,omitempty" jsonschema:"Run linter after tests (default: true)"`
	AutoFix  *bool  `json:"auto_fix,omitempty" jsonschema:"Run go mod tidy / go fmt before build (default: true)"`
}

// Runner defines the interface for running commands.
type Runner interface {
	Run(ctx context.Context, dir, name string, args ...string) error
	RunWithOutput(ctx context.Context, dir, name string, args ...string) (string, error)
	LookPath(file string) (string, error)
}

type stdRunner struct{}

func (r *stdRunner) Run(ctx context.Context, dir, name string, args ...string) error {
	cmd := exec.CommandContext(ctx, name, args...)
	cmd.Dir = dir
	return cmd.Run()
}

func (r *stdRunner) RunWithOutput(ctx context.Context, dir, name string, args ...string) (string, error) {
	cmd := exec.CommandContext(ctx, name, args...)
	cmd.Dir = dir
	out, err := cmd.CombinedOutput()
	return string(out), err
}

func (r *stdRunner) LookPath(file string) (string, error) {
	return exec.LookPath(file)
}

var CommandRunner Runner = &stdRunner{}

func Handler(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	dir := args.Dir
	if dir == "" {
		dir = "."
	}
	pkgs := args.Packages
	if pkgs == "" {
		pkgs = "./..."
	}

	// Defaults
	runTests := true
	if args.RunTests != nil {
		runTests = *args.RunTests
	}
	runLint := true
	if args.RunLint != nil {
		runLint = *args.RunLint
	}
	autoFix := true
	if args.AutoFix != nil {
		autoFix = *args.AutoFix
	}

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("# Smart Build Report (`%s`)\n\n", pkgs))

	// 1. Auto-Fix
	if autoFix {
		if err := CommandRunner.Run(ctx, dir, "go", "mod", "tidy"); err != nil {
			sb.WriteString(fmt.Sprintf("### ⚠️ Auto-Fix: `go mod tidy` Failed\n> %v\n\n", err))
		}
		if err := CommandRunner.Run(ctx, dir, "gofmt", "-w", "."); err != nil {
			// gofmt might fail if syntax is very broken, which build will catch
		}
	}

	// 2. Build
	sb.WriteString("### 🛠️ Build: ")
	buildOut, buildErr := CommandRunner.RunWithOutput(ctx, dir, "go", "build", pkgs)
	if buildErr != nil {
		sb.WriteString("❌ FAILED\n\n")
		sb.WriteString(formatOutput(buildOut))
		sb.WriteString(shared.GetDocHintFromOutput(buildOut))
		return result(sb.String(), true), nil, nil
	}
	sb.WriteString("✅ PASS\n\n")

	// 3. Tests
	if runTests {
		sb.WriteString("### 🧪 Tests: ")
		// -v for verbose to see which tests run
		testOut, testErr := CommandRunner.RunWithOutput(ctx, dir, "go", "test", "-v", pkgs)
		if testErr != nil {
			sb.WriteString("❌ FAILED\n\n")
			sb.WriteString(formatOutput(testOut))
			return result(sb.String(), true), nil, nil
		}
		sb.WriteString("✅ PASS\n\n")
	}

	// 4. Lint
	if runLint {
		sb.WriteString("### 🧹 Lint: ")

		// Check for golangci-lint
		lintCmd := "golangci-lint"
		lintArgs := []string{"run", pkgs}

		if _, err := CommandRunner.LookPath("golangci-lint"); err != nil {
			lintCmd = "go"
			lintArgs = []string{"vet", pkgs}
			sb.WriteString("(using `go vet`) ")
		}

		lintOut, lintErr := CommandRunner.RunWithOutput(ctx, dir, lintCmd, lintArgs...)
		if lintErr != nil {
			sb.WriteString("⚠️ ISSUES FOUND\n\n")
			sb.WriteString(formatOutput(lintOut))
			return result(sb.String(), true), nil, nil
		}
		sb.WriteString("✅ PASS\n")
	}

	return result(sb.String(), false), nil, nil
}

func formatOutput(out string) string {
	if out == "" {
		return ""
	}
	// Cap output to prevent massive context context usage
	if len(out) > 5000 {
		out = out[:2500] + "\n... [truncated] ...\n" + out[len(out)-2500:]
	}
	return "```text\n" + strings.TrimSpace(out) + "\n```\n"
}

func result(content string, isError bool) *mcp.CallToolResult {
	return &mcp.CallToolResult{
		IsError: isError,
		Content: []mcp.Content{
			&mcp.TextContent{Text: content},
		},
	}
}

// Package test implements the go test tool.
package test

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"strings"

	"github.com/danicat/godoctor/internal/toolnames"
	"github.com/danicat/godoctor/internal/tools/shared"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Register registers the tool with the server.
func Register(server *mcp.Server) {
	def := toolnames.Registry["go_test"]
	mcp.AddTool(server, &mcp.Tool{
		Name:        def.Name,
		Title:       def.Title,
		Description: def.Description,
	}, Handler)
}

// Params defines the input parameters.
type Params struct {
	Dir      string   `json:"dir,omitempty" jsonschema:"Directory to run tests in (default: current)"`
	Packages []string `json:"packages,omitempty" jsonschema:"Packages to list (default: ./...)"`
	Run      string   `json:"run,omitempty" jsonschema:"Run only those tests matching the regular expression."`
	Verbose  bool     `json:"verbose,omitempty" jsonschema:"Run tests in verbose mode (-v)"`
	Coverage bool     `json:"coverage,omitempty" jsonschema:"Run tests with coverage analysis (-cover)"`
	Args     []string `json:"args,omitempty" jsonschema:"Additional test arguments (e.g. -bench, -count, -failfast)"`
}

func Handler(ctx context.Context, _ *mcp.CallToolRequest, args Params) (*mcp.CallToolResult, any, error) {
	dir := args.Dir
	if dir == "" {
		dir = "."
	}
	pkgs := args.Packages
	if len(pkgs) == 0 {
		pkgs = []string{"./..."}
	}

	cmdArgs := []string{"test"}
	if args.Verbose {
		cmdArgs = append(cmdArgs, "-v")
	}

	var covFile string
	if args.Coverage {
		// Create temp file for coverage profile
		f, err := os.CreateTemp(dir, "coverage-*.out")
		if err == nil {
			covFile = f.Name()
			f.Close()
			defer os.Remove(covFile)
			// Use -coverpkg=./... to get coverage across all packages in the project
			cmdArgs = append(cmdArgs, "-cover", fmt.Sprintf("-coverprofile=%s", covFile), "-coverpkg=./...")
		} else {
			// Fallback to basic coverage if temp file creation fails
			cmdArgs = append(cmdArgs, "-cover")
		}
	}

	if args.Run != "" {
		cmdArgs = append(cmdArgs, "-run", args.Run)
	}
	cmdArgs = append(cmdArgs, args.Args...)
	cmdArgs = append(cmdArgs, pkgs...)

	cmd := exec.CommandContext(ctx, "go", cmdArgs...)
	cmd.Dir = dir

	out, err := cmd.CombinedOutput()
	output := string(out)

	// Process coverage if profile was created
	if covFile != "" {
		covCmd := exec.CommandContext(ctx, "go", "tool", "cover", fmt.Sprintf("-func=%s", covFile))
		covCmd.Dir = dir
		covOut, covErr := covCmd.CombinedOutput()
		if covErr == nil {
			lines := strings.Split(string(covOut), "\n")
			for _, line := range lines {
				if strings.HasPrefix(line, "total:") {
					output += "\n\n" + line
					break
				}
			}
		}
	}

	if err != nil {
		if output == "" {
			output = fmt.Sprintf("Tests failed: %v", err)
		} else {
			output = "Tests Failed:\n" + output
		}
		output += shared.GetDocHintFromOutput(output)
	} else {
		if output == "" {
			output = "Tests Passed (No output)."
		} else {
			// Often 'pass' is last line
			output = "Tests Passed:\n" + output
		}
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: output},
		},
	}, nil, nil
}

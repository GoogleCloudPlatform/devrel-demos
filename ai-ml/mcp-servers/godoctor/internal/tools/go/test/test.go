// Package test implements the go test tool.
package test

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"regexp"
	"strings"

	"github.com/danicat/godoctor/internal/toolnames"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// Register registers the tool with the server.
func Register(server *mcp.Server) {
	def := toolnames.Registry["verify_tests"]
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

	// ALWAYS use -json for smart parsing
	cmdArgs := []string{"test", "-json"}
	if args.Verbose {
		cmdArgs = append(cmdArgs, "-v")
	}

	var covFile string
	if args.Coverage {
		f, err := os.CreateTemp(dir, "coverage-*.out")
		if err == nil {
			covFile = f.Name()
			f.Close()
			defer os.Remove(covFile)
			cmdArgs = append(cmdArgs, "-cover", fmt.Sprintf("-coverprofile=%s", covFile))
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

	// 1. Parse JSON Output
	report := parseTestOutput(out)

	// 2. Process coverage
	var totalCoverage string
	if covFile != "" {
		covCmd := exec.CommandContext(ctx, "go", "tool", "cover", fmt.Sprintf("-func=%s", covFile))
		covCmd.Dir = dir
		covOut, covErr := covCmd.CombinedOutput()
		if covErr == nil {
			lines := strings.Split(string(covOut), "\n")
			for _, line := range lines {
				if strings.HasPrefix(line, "total:") {
					totalCoverage = line
					break
				}
			}
		}
	}

	// 3. Build Markdown Report
	var sb strings.Builder
	statusEmoji := "🟢"
	if report.Failed > 0 {
		statusEmoji = "🔴"
	}

	sb.WriteString(fmt.Sprintf("## %s Test Report: %s\n\n", statusEmoji, report.Summary()))
	if totalCoverage != "" {
		// totalCoverage looks like: "total: (statements) 37.9%"
		parts := strings.Fields(totalCoverage)
		if len(parts) >= 3 {
			sb.WriteString(fmt.Sprintf("📊 **Total Coverage:** %s\n\n", parts[len(parts)-1]))
		} else {
			sb.WriteString(fmt.Sprintf("📊 **Total Coverage:** %s\n\n", strings.TrimPrefix(totalCoverage, "total:")))
		}
	}

	if len(report.Failures) > 0 {
		sb.WriteString("### ❌ Failures\n")
		for _, f := range report.Failures {
			sb.WriteString(fmt.Sprintf("#### %s\n```text\n%s\n```\n", f.Name, f.Output))
		}
	}

	if len(report.Packages) > 0 {
		sb.WriteString("### 📦 Package Summary\n")
		sb.WriteString("| Package | Result | Tests | Coverage |\n")
		sb.WriteString("| :--- | :--- | :--- | :--- |\n")
		for _, p := range report.Packages {
					res := "✅ PASS"
					if p.Failed > 0 {
						res = "❌ FAIL"
					} else if p.NoTests || p.Total == 0 {
						res = "⚪ EMPTY"
					} else if p.Skipped {
						res = "⚠️ SKIP"
					}			
			cov := p.Coverage
			if cov == "" {
				cov = "-"
			}
			sb.WriteString(fmt.Sprintf("| %s | %s | %d/%d | %s |\n", p.Path, res, p.Passed, p.Total, cov))
		}
	}

	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: sb.String()},
		},
		IsError: err != nil && report.Failed > 0, // Error if tests failed
	}, nil, nil
}

type testReport struct {
	Passed   int
	Failed   int
	Skipped  int
	Packages []packageResult
	Failures []testFailure
}

type packageResult struct {
	Path     string
	Passed   int
	Failed   int
	Total    int
	Coverage string
	Skipped  bool
	NoTests  bool
}

type testFailure struct {
	Name   string
	Output string
}

func (r *testReport) Summary() string {
	return fmt.Sprintf("Passed: %d, Failed: %d, Skipped: %d", r.Passed, r.Failed, r.Skipped)
}

func parseTestOutput(raw []byte) testReport {
	report := testReport{}
	pkgMap := make(map[string]*packageResult)
	failureMap := make(map[string]*strings.Builder)

	// Regex to extract coverage percentage: "coverage: 72.7% of statements"
	// We want "72.7%"
	covRegex := regexp.MustCompile(`coverage:\s+(\d+\.\d+)%`)

	lines := strings.Split(string(raw), "\n")
	for _, line := range lines {
		if line == "" {
			continue
		}
		var event struct {
			Action  string
			Package string
			Test    string
			Output  string
			Elapsed float64
		}
		if err := json.Unmarshal([]byte(line), &event); err != nil {
			continue // Skip non-json lines
		}

		p, ok := pkgMap[event.Package]
		if !ok {
			p = &packageResult{Path: event.Package}
			pkgMap[event.Package] = p
		}

		switch event.Action {
		case "pass":
			if event.Test != "" {
				report.Passed++
				p.Passed++
				p.Total++
			}
		case "fail":
			if event.Test != "" {
				report.Failed++
				p.Failed++
				p.Total++
			}
		case "skip":
			if event.Test != "" {
				report.Skipped++
				p.Total++
			} else {
				p.Skipped = true
			}
		case "output":
			if strings.Contains(event.Output, "[no test files]") {
				p.NoTests = true
			}
			if event.Test != "" {
				// Buffer output for failing tests
				builder, ok := failureMap[event.Package+":"+event.Test]
				if !ok {
					builder = &strings.Builder{}
					failureMap[event.Package+":"+event.Test] = builder
				}
				builder.WriteString(event.Output)
			} else {
				// Parse package coverage from output if present
				// Format: "coverage: 80.0% of statements"
				if matches := covRegex.FindStringSubmatch(event.Output); len(matches) > 1 {
					p.Coverage = matches[1] + "%"
				}
			}
		}
	}

	for _, p := range pkgMap {
		report.Packages = append(report.Packages, *p)
	}

	return report
}

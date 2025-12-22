package report

import (
	"bytes"
	"fmt"
	"io"
	"os"
	"os/exec"
	"strings"
	"text/tabwriter"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/runner"
)

// Reporter generates reports from run results.
type Reporter struct {
	Results []runner.Result
	Out     io.Writer
	Cfg     *config.Configuration
	Notes   []string
}

// New creates a new Reporter.
func New(results []runner.Result, out io.Writer, cfg *config.Configuration, notes []string) *Reporter {
	return &Reporter{
		Results: results,
		Out:     out,
		Cfg:     cfg,
		Notes:   notes,
	}
}

// IsResultSuccessful returns true if the run result is considered a success.
func IsResultSuccessful(res runner.Result) bool {
	return res.Success()
}

// GenerateConsoleReport prints a summary table to the configured output.
func (r *Reporter) GenerateConsoleReport() {
	w := tabwriter.NewWriter(r.Out, 0, 0, 3, ' ', 0)
	fmt.Fprintln(w, "Alternative\tScenario\tRep\tDur\tTokens\tTools\tTest\tLint\tStatus")

	for _, res := range r.Results {
		isSuccess := IsResultSuccessful(res)
		status := "✅"
		if !isSuccess {
			if res.Error != nil && strings.Contains(res.Error.Error(), "timeout") {
				status = "⏱️ (Timeout)"
			} else {
				status = "❌ (Fail)"
			}
		} else if res.ValidationReport != "" {
			status = "✅ (Pass)"
		} else if res.AgentMetrics != nil && res.AgentMetrics.LoopDetected {
			status = "🔄 (Loop)"
		}

		tokens := 0
		toolCalls := 0
		if res.AgentMetrics != nil {
			tokens = res.AgentMetrics.TotalTokens
			toolCalls = len(res.AgentMetrics.ToolCalls)
		}

		testStatus := "-"
		lintIssues := 0
		if res.EvaluationMetrics != nil {
			if res.EvaluationMetrics.TestsFailed > 0 {
				testStatus = "FAIL"
			} else if res.EvaluationMetrics.TestsPassed > 0 {
				testStatus = "PASS"
			}
			lintIssues = res.EvaluationMetrics.LintIssues
		}

		fmt.Fprintf(w, "%s\t%s\t%d\t%s\t%d\t%d\t%s\t%d\t%s\n",
			res.Alternative,
			res.Scenario,
			res.Repetition,
			res.Duration.Round(time.Millisecond),
			tokens,
			toolCalls,
			testStatus,
			lintIssues,
			status,
		)
	}
	w.Flush()
}

// GenerateMarkdownReport creates an enhanced markdown report file.
func (r *Reporter) GenerateMarkdownReport(path string) error {
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()

	return r.GenerateMarkdown(f)
}

// GenerateMarkdown writes the enhanced markdown report to the provided writer.
func (r *Reporter) GenerateMarkdown(w io.Writer) error {
	gen := &EnhancedMarkdownGenerator{
		Results: r.Results,
		Cfg:     r.Cfg,
		Notes:   r.Notes,
		w:       w,
	}

	return gen.Generate()
}

// generateConclusion calls Gemini to summarize the results
func (r *Reporter) generateConclusion() (string, error) {
	// Construct a simple prompt with summarized data
	var b bytes.Buffer
	fmt.Fprintln(&b, "Analyze the following experiment results and provide a 1-paragraph conclusion on which alternative performed better.")
	fmt.Fprintln(&b, "Critically Important: Identify failures. A run with 'Status=FAIL' or 'Status=CRASH' is a negative result, regardless of speed/tokens.")
	fmt.Fprintln(&b, "Data:")
	for _, res := range r.Results {
		status := "SUCCESS"
		if res.Error != nil {
			status = "CRASH"
		}

		tokens := 0
		if res.AgentMetrics != nil {
			tokens = res.AgentMetrics.TotalTokens
		}

		lint := 0
		if res.EvaluationMetrics != nil {
			lint = res.EvaluationMetrics.LintIssues
			if res.EvaluationMetrics.TestsPassed == 0 || res.EvaluationMetrics.TestsFailed > 0 {
				status = "FAIL"
			}
		}

		fmt.Fprintf(&b, "- Alt='%s', Scen='%s', Time=%s, Tokens=%d, Lint=%d, Status=%s\n",
			res.Alternative, res.Scenario, res.Duration.Round(time.Millisecond), tokens, lint, status)
	}

	// Call Gemini using stdin pipe and capturing stdout only
	cmd := exec.Command("gemini", "--output-format", "text")
	cmd.Stdin = &b
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr // Capture logs here to discard them or print on debug

	if err := cmd.Run(); err != nil {
		return "", fmt.Errorf("gemini call failed: %v (stderr: %s)", err, stderr.String())
	}

	return strings.TrimSpace(stdout.String()), nil
}

package report

import (
	"bytes"
	"context"
	"fmt"
	"os/exec"
	"strings"
	"time"
)

// generateConclusion calls Gemini to summarize the results
func (r *Reporter) generateConclusion() (string, error) {
	// ... (prompt construction)
	// I'll skip prompt construction for brevity but include it in the replace.

	// Construct a simple prompt with summarized data
	var b bytes.Buffer
	fmt.Fprintln(&b, "Analyze the following experiment results and provide a 1-paragraph conclusion on which alternative performed better.")
	fmt.Fprintln(&b, "Critically Important: Identify failures. A run with 'Status=FAIL' or 'Status=CRASH' is a negative result, regardless of speed/tokens.")
	fmt.Fprintln(&b, "Data:")
	for _, res := range r.Results {
		status := "SUCCESS"
		if res.ErrorStr != "" {
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
	ctx, cancel := context.WithTimeout(context.Background(), 2*time.Minute)
	defer cancel()

	cmd := exec.CommandContext(ctx, "gemini", "--output-format", "text")
	cmd.Stdin = &b
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr // Capture logs here to discard them or print on debug

	if err := cmd.Run(); err != nil {
		return "", fmt.Errorf("gemini call failed: %v (stderr: %s)", err, stderr.String())
	}

	return strings.TrimSpace(stdout.String()), nil
}

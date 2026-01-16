package report

import (
	"fmt"
	"strings"
	"text/tabwriter"
	"time"
)

// GenerateConsoleReport prints a summary table to the configured output.
func (r *Reporter) GenerateConsoleReport() error {
	w := tabwriter.NewWriter(r.Out, 0, 0, 3, ' ', 0)
	fmt.Fprintln(w, "Alternative\tScenario\tRep\tDur\tTokens\tTools\tTest\tLint\tStatus")

	for _, res := range r.Results {
		isSuccess := res.IsSuccess
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
			toolCalls = res.AgentMetrics.TotalToolCallsCount
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

		_, _ = fmt.Fprintf(w, "%s\t%s\t%d\t%s\t%d\t%d\t%s\t%d\t%s\n",
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
	return w.Flush()
}

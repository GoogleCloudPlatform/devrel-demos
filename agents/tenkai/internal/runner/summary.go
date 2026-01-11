package runner

import (
	"strings"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db/models"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/stats"
)

// ExperimentSummary holds the aggregated results for the entire experiment.
type ExperimentSummary struct {
	TotalRuns      int                                    `json:"total_runs"`
	SuccessfulRuns int                                    `json:"successful_runs"`
	SuccessRate    float64                                `json:"success_rate"`
	AvgDuration    float64                                `json:"avg_duration"` // seconds
	AvgTokens      float64                                `json:"avg_tokens"`
	TotalLint      int                                    `json:"total_lint"`
	Alternatives   map[string]models.ExperimentSummaryRow `json:"alternatives"`
}

func CalculateSummary(results []Result, controlAlt string, allAlts []string) *ExperimentSummary {
	summary := &ExperimentSummary{
		TotalRuns:    0,
		Alternatives: make(map[string]models.ExperimentSummaryRow),
	}

	// Pre-populate all expected alternatives
	for _, name := range allAlts {
		summary.Alternatives[name] = models.ExperimentSummaryRow{
			Alternative:  name,
			PSuccess:     -1.0,
			PDuration:    -1.0,
			PTokens:      -1.0,
			PLint:        -1.0,
			PTestsPassed: -1.0,
			PTestsFailed: -1.0,
			PTimeout:     -1.0,
		}
	}

	if len(results) == 0 {
		return summary
	}

	type intermediate struct {
		totalRuns       int
		successes       int
		timeouts        int
		totalTokens     int64
		totalLint       int
		totalDur        time.Duration
		totalToolCalls  int
		failedToolCalls int
		durations       []float64
		tokens          []float64
		lints           []float64
		passes          []float64
		failures        []float64
	}

	byAlt := make(map[string]*intermediate)
	altNames := []string{}
	for _, res := range results {
		// Only count terminal statuses in the summary metrics
		// We use strict COMPLETED check to ensure we don't count partial runs
		status := strings.ToUpper(res.Status)
		if status != db.RunStatusCompleted {
			continue
		}

		// Filter out ABORTED runs (statistically void)
		if strings.ToUpper(res.Reason) == "ABORTED" {
			continue
		}

		summary.TotalRuns++

		if _, ok := byAlt[res.Alternative]; !ok {
			byAlt[res.Alternative] = &intermediate{}
			altNames = append(altNames, res.Alternative)
		}
		m := byAlt[res.Alternative]
		m.totalRuns++

		m.totalDur += res.Duration
		m.durations = append(m.durations, res.Duration.Seconds())

		if res.IsSuccess {
			m.successes++
			summary.SuccessfulRuns++
		} else if res.IsTimeout() {
			m.timeouts++
		}

		if res.AgentMetrics != nil {
			m.totalTokens += int64(res.AgentMetrics.TotalTokens)
			m.tokens = append(m.tokens, float64(res.AgentMetrics.TotalTokens))
		}
		if res.Error == nil && res.AgentMetrics != nil {
			m.totalToolCalls += res.AgentMetrics.TotalToolCallsCount
			m.failedToolCalls += res.AgentMetrics.FailedToolCalls
		}

		if res.EvaluationMetrics != nil {
			m.totalLint += res.EvaluationMetrics.LintIssues
			summary.TotalLint += res.EvaluationMetrics.LintIssues
			m.lints = append(m.lints, float64(res.EvaluationMetrics.LintIssues))
			m.passes = append(m.passes, float64(res.EvaluationMetrics.TestsPassed))
			m.failures = append(m.failures, float64(res.EvaluationMetrics.TestsFailed))
		}
	}

	summary.SuccessRate = float64(summary.SuccessfulRuns) / float64(summary.TotalRuns) * 100

	var totalSuccessDur time.Duration
	var totalSuccessTokens int64

	for _, name := range allAlts {
		m, ok := byAlt[name]
		if !ok {
			continue
		}
		as := models.ExperimentSummaryRow{
			Alternative:     name,
			TotalRuns:       m.totalRuns,
			SuccessCount:    m.successes,
			SuccessRate:     float64(m.successes) / float64(m.totalRuns) * 100,
			AvgLint:         float64(m.totalLint) / float64(m.totalRuns),
			Timeouts:        m.timeouts,
			TotalToolCalls:  m.totalToolCalls,
			FailedToolCalls: m.failedToolCalls,
		}

		if m.totalRuns > 0 {
			as.AvgDuration = (m.totalDur / time.Duration(m.totalRuns)).Seconds()
			if m.totalRuns > 0 {
				as.AvgTokens = float64(m.totalTokens) / float64(m.totalRuns)
			}

			totalSuccessDur += m.totalDur
			totalSuccessTokens += m.totalTokens
		}

		var totalPass, totalFail float64
		for _, x := range m.passes {
			totalPass += x
		}
		for _, x := range m.failures {
			totalFail += x
		}
		if len(m.passes) > 0 {
			as.AvgTestsPassed = totalPass / float64(len(m.passes))
		}
		if len(m.failures) > 0 {
			as.AvgTestsFailed = totalFail / float64(len(m.failures))
		}

		summary.Alternatives[name] = as
	}

	if summary.TotalRuns > 0 {
		summary.AvgDuration = (totalSuccessDur / time.Duration(summary.TotalRuns)).Seconds()
		summary.AvgTokens = float64(totalSuccessTokens) / float64(summary.TotalRuns)
	}

	// Stats vs Control
	if controlAlt == "" && len(altNames) > 0 {
		controlAlt = altNames[0]
	}

	if controlData, ok := byAlt[controlAlt]; ok {
		for name, as := range summary.Alternatives {
			if name == controlAlt {
				continue
			}
			m, ok := byAlt[name]
			if !ok {
				continue
			}

			// Initialize with Sentinel
			as.PSuccess = -1.0
			as.PDuration = -1.0
			as.PTokens = -1.0
			as.PLint = -1.0
			as.PTestsPassed = -1.0
			as.PTestsFailed = -1.0
			as.PTimeout = -1.0

			// Statistical tests require at least 2 samples in BOTH groups for t-tests
			if controlData.totalRuns >= 2 && m.totalRuns >= 2 {
				as.PDuration = stats.WelchTTest(controlData.durations, m.durations)
				as.PTokens = stats.WelchTTest(controlData.tokens, m.tokens)
				as.PLint = stats.WelchTTest(controlData.lints, m.lints)
				as.PTestsPassed = stats.WelchTTest(controlData.passes, m.passes)
				as.PTestsFailed = stats.WelchTTest(controlData.failures, m.failures)
			}

			// Fisher's Exact Test
			// We can run this even with N=1, but for consistency with "Statistical Analysis" usually implying N>=2
			// and to avoid noise, we keep the N>=2 gate.
			if controlData.totalRuns >= 2 && m.totalRuns >= 2 {
				as.PSuccess = stats.FisherExactTest(
					controlData.successes, controlData.totalRuns-controlData.successes,
					m.successes, m.totalRuns-m.successes,
				)
				as.PTimeout = stats.FisherExactTest(
					controlData.timeouts, controlData.totalRuns-controlData.timeouts,
					m.timeouts, m.totalRuns-m.timeouts,
				)
			}
			summary.Alternatives[name] = as
		}
	}

	return summary
}

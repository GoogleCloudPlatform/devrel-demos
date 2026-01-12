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
			PToolCalls:   -1.0,
		}
	}

	if len(results) == 0 {
		return summary
	}

	type intermediate struct {
		totalRuns        int
		successes        int
		timeouts         int
		totalTokens      int64
		totalLint        int
		totalDur         time.Duration
		totalToolCalls   int
		failedToolCalls  int
		durations        []float64
		tokens           []float64
		lints            []float64
		passes           []float64
		failures         []float64
		toolCalls        []float64
		toolUsageAll     map[string][]float64 // Tool Name -> []Count aligned with durations/tokens
		toolUsageSuccess map[string][]float64 // Tool Name -> []Count (Success only)
		toolUsageFail    map[string][]float64 // Tool Name -> []Count (Fail only)
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
			byAlt[res.Alternative] = &intermediate{
				toolUsageAll:     make(map[string][]float64),
				toolUsageSuccess: make(map[string][]float64),
				toolUsageFail:    make(map[string][]float64),
			}
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
			m.totalToolCalls += res.AgentMetrics.TotalToolCallsCount
			m.failedToolCalls += res.AgentMetrics.FailedToolCalls
			m.toolCalls = append(m.toolCalls, float64(res.AgentMetrics.TotalToolCallsCount))
		}

		if res.EvaluationMetrics != nil {
			m.totalLint += res.EvaluationMetrics.LintIssues
			summary.TotalLint += res.EvaluationMetrics.LintIssues
			m.lints = append(m.lints, float64(res.EvaluationMetrics.LintIssues))
			m.passes = append(m.passes, float64(res.EvaluationMetrics.TestsPassed))
			m.failures = append(m.failures, float64(res.EvaluationMetrics.TestsFailed))
		}

		// Tool Usage Extraction for Stats
		runToolCounts := make(map[string]int)
		if res.AgentMetrics != nil {
			for _, tc := range res.AgentMetrics.ToolCalls {
				runToolCounts[tc.Name]++
			}
		}

		// To ensure alignment, we need to know ALL potential tools or just build proactively.
		// For Correlation, we need strict alignment with m.durations / m.tokens (which we just appended to)
		// We can't know the full set of tools yet, so we have to store ragged arrays or just use what we have.
		// BETTER APPROACH: Only track tools that *appear* in this run, but for correlation we need X and Y to be same length.
		// Solution: We will "backfill" zeros later or just keep sparse? No, Spearman needs full vector.
		// Actually, we can just lazy-initialize the slice for a tool to length of (totalRuns-1) with 0s? No, totalRuns grows.
		// Simplest: Just don't rely on pre-filled structure for correlation if it's ragged.
		// But let's try to fill it.

		// We'll iterate known tools in the map later to fill zeros? No, that's complex.
		// Let's just track per-run usage here.
		for tool, count := range runToolCounts {
			// Ensure slice exists
			if _, ok := m.toolUsageAll[tool]; !ok {
				// We might have missed previous runs. We need to backfill zeros?
				// This is getting tricky.
				// Alternative: Store []int of usage for EACH run in a single struct, then pivot later.
			}
			_ = count
		}

		// RE-STRATEGY: Store full tool map per run.
		// Let's just create a temporary slice of results for later analysis.

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
			PSuccess:        -1.0,
			PDuration:       -1.0,
			PTokens:         -1.0,
			PLint:           -1.0,
			PTestsPassed:    -1.0,
			PTestsFailed:    -1.0,
			PTimeout:        -1.0,
			PToolCalls:      -1.0,
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

			// Statistical tests require sufficient sample size (N>=5) to be trustworthy
			// and to satisfy assumptions (approx normality for t-test).
			if controlData.totalRuns >= 5 && m.totalRuns >= 5 {
				as.PDuration = stats.WelchTTest(controlData.durations, m.durations)
				as.PTokens = stats.WelchTTest(controlData.tokens, m.tokens)
				as.PLint = stats.WelchTTest(controlData.lints, m.lints)
				as.PTestsPassed = stats.WelchTTest(controlData.passes, m.passes)
				as.PTestsFailed = stats.WelchTTest(controlData.failures, m.failures)
				as.PToolCalls = stats.WelchTTest(controlData.toolCalls, m.toolCalls)
			}

			// Fisher's Exact Test (also enforcing N>=5 for consistency/believability)
			if controlData.totalRuns >= 5 && m.totalRuns >= 5 {
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

	// Tool Analysis (Per Alternative) - Re-scanning required for alignment
	// We need to build continuous vectors for each tool to correlate with duration/tokens.
	for name, as := range summary.Alternatives { // Iterate summary to modify it

		// Get the original results for this alternative to build aligned vectors
		var altResults []Result
		for _, res := range results {
			if res.Alternative == name && strings.ToUpper(res.Status) == db.RunStatusCompleted && strings.ToUpper(res.Reason) != "ABORTED" {
				altResults = append(altResults, res)
			}
		}

		if len(altResults) < 5 { // Skip stats for tiny samples
			continue
		}

		// collecting vectors
		var durations []float64
		var tokens []float64

		// Map: ToolName -> []float64 (counts per run, aligned with durations)
		toolCounts := make(map[string][]float64)

		// Separate vectors for Success vs Fail
		toolCountsSucc := make(map[string][]float64) // not aligned, just bucketed
		toolCountsFail := make(map[string][]float64)

		for _, res := range altResults {
			durations = append(durations, res.Duration.Seconds())
			tks := 0.0
			if res.AgentMetrics != nil {
				tks = float64(res.AgentMetrics.TotalTokens)
			}
			tokens = append(tokens, tks)

			// Count for this run
			runCounts := make(map[string]float64)
			if res.AgentMetrics != nil {
				for _, tc := range res.AgentMetrics.ToolCalls {
					runCounts[tc.Name]++
				}
			}

			// Add to aligned global map (we'll fix missing keys later?
			// No, we need to know specific tools beforehand OR iterate all seen tools later.
			// Let's collect ALL seen tools first.)
			for t, c := range runCounts {
				if _, exists := toolCounts[t]; !exists {
					toolCounts[t] = make([]float64, 0, len(altResults))
				}
				_ = c
			}
		}

		// Second pass to fill vectors with 0 padding
		// First identify ALL tools seen in this alternative
		allSeenTools := make(map[string]bool)
		for _, res := range altResults {
			if res.AgentMetrics != nil {
				for _, tc := range res.AgentMetrics.ToolCalls {
					allSeenTools[tc.Name] = true
				}
			}
		}

		// Initialize vectors
		for t := range allSeenTools {
			toolCounts[t] = make([]float64, len(altResults))
		}

		// Populate vectors
		for i, res := range altResults {
			if res.AgentMetrics != nil {
				for _, tc := range res.AgentMetrics.ToolCalls {
					toolCounts[tc.Name][i]++
				}
			}
		}

		// Populate Success/Fail buckets
		for i, res := range altResults {
			for t := range allSeenTools {
				val := toolCounts[t][i]
				if res.IsSuccess {
					toolCountsSucc[t] = append(toolCountsSucc[t], val)
				} else {
					toolCountsFail[t] = append(toolCountsFail[t], val)
				}
			}
		}

		// Compute Stats
		var analysisList []models.ToolAnalysis
		for t := range allSeenTools {
			row := models.ToolAnalysis{
				ToolName:       t,
				SuccFailPValue: -1.0,
			}

			// 1. Success vs Fail
			s := toolCountsSucc[t]
			f := toolCountsFail[t]
			if len(s) >= 2 && len(f) >= 2 {
				row.SuccFailPValue = stats.MannWhitneyU(s, f)
			}

			// 2. Correlation
			// Variance check to avoid NaN
			if stats.Variance(toolCounts[t]) > 0 && stats.Variance(durations) > 0 {
				row.DurationCorr = stats.SpearmanCorrelation(toolCounts[t], durations)
			}
			if stats.Variance(toolCounts[t]) > 0 && stats.Variance(tokens) > 0 {
				row.TokensCorr = stats.SpearmanCorrelation(toolCounts[t], tokens)
			}

			analysisList = append(analysisList, row)
		}

		as.ToolAnalysis = analysisList
		summary.Alternatives[name] = as
	}

	return summary
}

package runner

import (
	"encoding/json"
	"strings"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db/models"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/stats"
)

type SummaryFilter string

const (
	FilterAll        SummaryFilter = "all"
	FilterCompleted  SummaryFilter = "completed"
	FilterSuccessful SummaryFilter = "successful"
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

func CalculateSummary(results []Result, controlAlt string, allAlts []string, toolCounts map[int64]map[string]int, filter SummaryFilter) *ExperimentSummary {
	summary := &ExperimentSummary{
		TotalRuns:    0,
		Alternatives: make(map[string]models.ExperimentSummaryRow),
	}

	// Pre-populate all expected alternatives
	for _, name := range allAlts {
		summary.Alternatives[name] = models.ExperimentSummaryRow{
			Alternative:      name,
			PSuccess:         -1.0,
			PDuration:        -1.0,
			PTokens:          -1.0,
			PInputTokens:     -1.0,
			POutputTokens:    -1.0,
			PCachedTokens:    -1.0,
			PLint:            -1.0,
			PCoverage:        -1.0,
			PTestsPassed:     -1.0,
			PTestsFailed:     -1.0,
			PTimeout:         -1.0,
			PToolCalls:       -1.0,
			PFailedToolCalls: -1.0,
			FailureReasons:   make(map[string]int),
			PFailureReasons:  make(map[string]float64),
		}
	}

	if len(results) == 0 {
		return summary
	}

	type intermediate struct {
		totalRuns          int
		successes          int
		timeouts           int
		totalTokens        int64
		totalInputTokens   int64
		totalOutputTokens  int64
		totalCachedTokens  int64
		totalLint          int
		totalCoverage      float64
		totalDur           time.Duration
		totalToolCalls     int
		failedToolCalls    int
		durations          []float64
		tokens             []float64
		inputTokens        []float64
		outputTokens       []float64
		cachedTokens       []float64
		lints              []float64
		coverages          []float64
		passes             []float64
		failures           []float64
		toolCalls          []float64
		failedToolCallsVec []float64
		failureReasons     map[string]int
		// Vectors for tool analysis are handled in analyzeTools now
	}

	byAlt := make(map[string]*intermediate)
	altNames := []string{}
	var validResults []Result // For Combined analysis

	for _, res := range results {
		status := strings.ToUpper(res.Status)
		if status != db.RunStatusCompleted {
			continue
		}
		if strings.ToUpper(res.Reason) == "ABORTED" {
			continue
		}

		// Filtering Logic
		// "all": Include everything that is COMPLETED (and not ABORTED)
		// "completed": Include Success OR Validation Failures (exclude timeouts, loops, errors)
		// "successful": Include Success only

		if filter == FilterSuccessful && !res.IsSuccess {
			continue
		}
		if filter == FilterCompleted {
			// "Completed Only" (User Def): Success + Validation Failures.
			// Exclude Timeout, Loop, Error.
			// IsSuccess true -> Keep
			// IsSuccess false -> Check Reason.
			if !res.IsSuccess {
				r := strings.ToUpper(res.Reason)
				if r != db.ReasonFailedValidation {
					continue
				}
			}
		}
		// FilterAll implicitly accepts everything reaching here

		validResults = append(validResults, res)
		summary.TotalRuns++

		if _, ok := byAlt[res.Alternative]; !ok {
			byAlt[res.Alternative] = &intermediate{
				failureReasons: make(map[string]int),
			}
			altNames = append(altNames, res.Alternative)
		}
		m := byAlt[res.Alternative]
		m.totalRuns++

		if res.AgentMetrics != nil {
			m.totalTokens += int64(res.AgentMetrics.TotalTokens)
			m.tokens = append(m.tokens, float64(res.AgentMetrics.TotalTokens))
			m.totalInputTokens += int64(res.AgentMetrics.InputTokens)
			m.inputTokens = append(m.inputTokens, float64(res.AgentMetrics.InputTokens))
			m.totalOutputTokens += int64(res.AgentMetrics.OutputTokens)
			m.outputTokens = append(m.outputTokens, float64(res.AgentMetrics.OutputTokens))
			m.totalCachedTokens += int64(res.AgentMetrics.CachedTokens)
			m.cachedTokens = append(m.cachedTokens, float64(res.AgentMetrics.CachedTokens))

			m.totalToolCalls += res.AgentMetrics.TotalToolCallsCount
			m.failedToolCalls += res.AgentMetrics.FailedToolCalls
			m.toolCalls = append(m.toolCalls, float64(res.AgentMetrics.TotalToolCallsCount))
			m.failedToolCallsVec = append(m.failedToolCallsVec, float64(res.AgentMetrics.FailedToolCalls))
		}

		if res.IsSuccess {
			m.successes++
			summary.SuccessfulRuns++

			m.totalDur += res.Duration
			m.durations = append(m.durations, res.Duration.Seconds())

			if res.EvaluationMetrics != nil {
				m.totalLint += res.EvaluationMetrics.LintIssues
				summary.TotalLint += res.EvaluationMetrics.LintIssues
				m.lints = append(m.lints, float64(res.EvaluationMetrics.LintIssues))
				m.passes = append(m.passes, float64(res.EvaluationMetrics.TestsPassed))
				m.failures = append(m.failures, float64(res.EvaluationMetrics.TestsFailed))

				// Extract Coverage from ValidationReport
				if res.ValidationReport != "" {
					var report ValidationReport
					if err := json.Unmarshal([]byte(res.ValidationReport), &report); err == nil {
						// Include coverage even if 0 to avoid bias
						m.totalCoverage += report.Coverage
						m.coverages = append(m.coverages, report.Coverage)
					}
				}
			}
		} else {
			// Failure Handling
			if res.IsTimeout() {
				m.timeouts++
			}
			reasons := GetFailureReasons(res)
			for _, r := range reasons {
				m.failureReasons[r]++
			}
		}
	}

	summary.SuccessRate = 0
	if summary.TotalRuns > 0 {
		summary.SuccessRate = float64(summary.SuccessfulRuns) / float64(summary.TotalRuns) * 100
	}

	var totalSuccessDur time.Duration
	var totalSuccessTokens int64

	for _, name := range allAlts {
		m, ok := byAlt[name]
		if !ok {
			continue
		}
		as := models.ExperimentSummaryRow{
			Alternative:      name,
			TotalRuns:        m.totalRuns,
			SuccessCount:     m.successes,
			SuccessRate:      0,
			AvgLint:          0,
			Timeouts:         m.timeouts,
			TotalToolCalls:   m.totalToolCalls,
			FailedToolCalls:  m.failedToolCalls,
			PSuccess:         -1.0,
			PDuration:        -1.0,
			PTokens:          -1.0,
			PInputTokens:     -1.0,
			POutputTokens:    -1.0,
			PCachedTokens:    -1.0,
			PLint:            -1.0,
			PCoverage:        -1.0,
			PTestsPassed:     -1.0,
			PTestsFailed:     -1.0,
			PTimeout:         -1.0,
			PToolCalls:       -1.0,
			PFailedToolCalls: -1.0,
			FailureReasons:   m.failureReasons,
			PFailureReasons:  make(map[string]float64),
		}

		if m.totalRuns > 0 {
			as.SuccessRate = float64(m.successes) / float64(m.totalRuns) * 100
			as.AvgLint = float64(m.totalLint) / float64(m.totalRuns)
			as.AvgDuration = (m.totalDur / time.Duration(m.totalRuns)).Seconds()
			as.AvgTokens = float64(m.totalTokens) / float64(m.totalRuns)
			as.AvgInputTokens = float64(m.totalInputTokens) / float64(m.totalRuns)
			as.AvgOutputTokens = float64(m.totalOutputTokens) / float64(m.totalRuns)
			as.AvgCachedTokens = float64(m.totalCachedTokens) / float64(m.totalRuns)

			if len(m.coverages) > 0 {
				as.AvgCoverage = m.totalCoverage / float64(len(m.coverages))
			} else {
				as.AvgCoverage = 0
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

		// Tool Analysis (Per Alternative)
		// Filter results for this alternative
		var altResults []Result
		for _, res := range validResults {
			if res.Alternative == name {
				altResults = append(altResults, res)
			}
		}
		as.ToolAnalysis = analyzeTools(altResults, toolCounts)

		summary.Alternatives[name] = as
	}

	if summary.TotalRuns > 0 {
		summary.AvgDuration = (totalSuccessDur / time.Duration(summary.TotalRuns)).Seconds()
		summary.AvgTokens = float64(totalSuccessTokens) / float64(summary.TotalRuns)
	}

	// Stats vs Control
	if controlData, ok := byAlt[controlAlt]; ok {
		for name, as := range summary.Alternatives {
			if name == controlAlt {
				continue
			}
			m, ok := byAlt[name]
			if !ok {
				continue
			}

			// P-Values (Welch / Fisher)
			// Checks individually per metric to ensure we have enough valid samples (N>=5)
			if len(controlData.durations) >= 5 && len(m.durations) >= 5 {
				as.PDuration = stats.WelchTTest(controlData.durations, m.durations)
				as.EffectDuration = stats.CohensD(m.durations, controlData.durations)
			}
			if len(controlData.tokens) >= 5 && len(m.tokens) >= 5 {
				as.PTokens = stats.WelchTTest(controlData.tokens, m.tokens)
				as.EffectTokens = stats.CohensD(m.tokens, controlData.tokens)

				as.PInputTokens = stats.WelchTTest(controlData.inputTokens, m.inputTokens)
				as.EffectInputTokens = stats.CohensD(m.inputTokens, controlData.inputTokens)

				as.POutputTokens = stats.WelchTTest(controlData.outputTokens, m.outputTokens)
				as.EffectOutputTokens = stats.CohensD(m.outputTokens, controlData.outputTokens)

				as.PCachedTokens = stats.WelchTTest(controlData.cachedTokens, m.cachedTokens)
				as.EffectCachedTokens = stats.CohensD(m.cachedTokens, controlData.cachedTokens)
			}
			if len(controlData.lints) >= 5 && len(m.lints) >= 5 {
				as.PLint = stats.WelchTTest(controlData.lints, m.lints)
				as.PTestsPassed = stats.WelchTTest(controlData.passes, m.passes)
				as.PTestsFailed = stats.WelchTTest(controlData.failures, m.failures)
			}
			if len(controlData.coverages) >= 5 && len(m.coverages) >= 5 {
				as.PCoverage = stats.WelchTTest(controlData.coverages, m.coverages)
				as.EffectCoverage = stats.CohensD(m.coverages, controlData.coverages)
			}
			if len(controlData.toolCalls) >= 5 && len(m.toolCalls) >= 5 {
				as.PToolCalls = stats.WelchTTest(controlData.toolCalls, m.toolCalls)
				as.PFailedToolCalls = stats.WelchTTest(controlData.failedToolCallsVec, m.failedToolCallsVec)
			}

			// Fisher's Exact Test uses total counts, so totalRuns is appropriate here
			if controlData.totalRuns >= 5 && m.totalRuns >= 5 {
				as.PSuccess = stats.FisherExactTest(controlData.successes, controlData.totalRuns-controlData.successes, m.successes, m.totalRuns-m.successes)
				as.PTimeout = stats.FisherExactTest(controlData.timeouts, controlData.totalRuns-controlData.timeouts, m.timeouts, m.totalRuns-m.timeouts)

				// Failure Reasons Analysis
				// Union of all failure reasons seen in both control and this alternative
				allReasons := make(map[string]bool)
				for r := range controlData.failureReasons {
					allReasons[r] = true
				}
				for r := range m.failureReasons {
					allReasons[r] = true
				}

				for r := range allReasons {
					ctrlCount := controlData.failureReasons[r]
					altCount := m.failureReasons[r]
					// Yes, No
					// No = TotalRuns - Yes
					as.PFailureReasons[r] = stats.FisherExactTest(ctrlCount, controlData.totalRuns-ctrlCount, altCount, m.totalRuns-altCount)
				}
			}
			summary.Alternatives[name] = as
		}
	}

	// Combined Analysis
	combinedFailures := make(map[string]int)
	for _, m := range byAlt {
		for r, count := range m.failureReasons {
			combinedFailures[r] += count
		}
	}

	combinedRow := models.ExperimentSummaryRow{
		Alternative:    "Combined",
		TotalRuns:      summary.TotalRuns,
		SuccessCount:   summary.SuccessfulRuns,
		SuccessRate:    summary.SuccessRate,
		ToolAnalysis:   analyzeTools(validResults, toolCounts),
		FailureReasons: combinedFailures,
	}
	summary.Alternatives["Combined"] = combinedRow

	return summary
}

func GetFailureReasons(res Result) []string {
	var reasons []string

	switch res.Reason {
	case db.ReasonFailedTimeout:
		reasons = append(reasons, "Execution Timeout")
	case db.ReasonFailedLoop:
		reasons = append(reasons, "Loop Detected")
	case db.ReasonFailedError:
		reasons = append(reasons, "Runtime Error")
	case db.ReasonFailedValidation:
		if res.ValidationReport == "" {
			reasons = append(reasons, "Missing Validation Report")
			return reasons
		}

		var report ValidationReport
		if err := json.Unmarshal([]byte(res.ValidationReport), &report); err != nil {
			reasons = append(reasons, "Corrupt Validation Report")
			return reasons
		}

		foundSpecific := false
		for _, item := range report.Items {
			if item.Status != "PASS" {
				foundSpecific = true
				switch item.Type {
				case "test":
					// Functional Test vs Coverage
					if strings.Contains(item.Details, "tests failed") && !strings.Contains(item.Details, "0 tests failed") {
						reasons = append(reasons, "Test Failure")
					}
					if strings.Contains(item.Details, "Requirement:") && strings.Contains(item.Details, "Cov:") {
						reasons = append(reasons, "Test Failure (Coverage)")
					}
				case "lint":
					reasons = append(reasons, "Lint Violation")
				case "command":
					reasons = append(reasons, "Command Failure")
				case "model":
					reasons = append(reasons, "Model Validation Failure")
				default:
					reasons = append(reasons, item.Type+" Failure")
				}
			}
		}
		if !foundSpecific {
			reasons = append(reasons, "Unknown Validation Failure")
		}
	default:
		if res.Reason != "" {
			reasons = append(reasons, res.Reason)
		} else {
			reasons = append(reasons, "Unknown Failure")
		}
	}

	// Dedup reasons
	unique := make(map[string]bool)
	var final []string
	for _, r := range reasons {
		if !unique[r] {
			unique[r] = true
			final = append(final, r)
		}
	}

	return final
}

func analyzeTools(results []Result, toolCounts map[int64]map[string]int) []models.ToolAnalysis {
	if len(results) < 5 {
		return nil
	}

	var durations []float64
	var tokens []float64
	var cachedTokens []float64

	// Map: ToolName -> []float64 (counts per run, aligned with durations)
	toolCountsMap := make(map[string][]float64)

	// Separate vectors for Success vs Fail
	toolCountsSucc := make(map[string][]float64)
	toolCountsFail := make(map[string][]float64)

	for _, res := range results {
		durations = append(durations, res.Duration.Seconds())
		tks := 0.0
		cached := 0.0
		if res.AgentMetrics != nil {
			tks = float64(res.AgentMetrics.TotalTokens)
			cached = float64(res.AgentMetrics.CachedTokens)
		}
		tokens = append(tokens, tks)
		cachedTokens = append(cachedTokens, cached)

		// Count for this run from authoritative map
		runCounts := toolCounts[res.RunID]
		if runCounts == nil {
			runCounts = make(map[string]int)
		}

		// Add to aligned global map to track keys
		for t := range runCounts {
			if _, exists := toolCountsMap[t]; !exists {
				toolCountsMap[t] = make([]float64, 0, len(results))
			}
		}
	}

	// Second pass: Identify ALL tools seen
	allSeenTools := make(map[string]bool)
	for _, res := range results {
		counts := toolCounts[res.RunID]
		for t := range counts {
			allSeenTools[t] = true
		}
	}

	// Initialize vectors
	perToolRunVectors := make(map[string][]float64)
	for t := range allSeenTools {
		perToolRunVectors[t] = make([]float64, len(results))
	}

	// Populate vectors
	for i, res := range results {
		counts := toolCounts[res.RunID]
		for t, count := range counts {
			perToolRunVectors[t][i] = float64(count)
		}
	}

	// Populate Success/Fail buckets
	for i, res := range results {
		for t := range allSeenTools {
			val := perToolRunVectors[t][i]
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
		if len(s) >= 5 && len(f) >= 5 {
			row.SuccFailPValue = stats.MannWhitneyU(s, f)
		}

		// 2. Correlation
		if stats.Variance(perToolRunVectors[t]) > 0 && stats.Variance(durations) > 0 {
			row.DurationCorr = stats.SpearmanCorrelation(perToolRunVectors[t], durations)
		}
		if stats.Variance(perToolRunVectors[t]) > 0 && stats.Variance(tokens) > 0 {
			row.TokensCorr = stats.SpearmanCorrelation(perToolRunVectors[t], tokens)
		}
		if stats.Variance(perToolRunVectors[t]) > 0 && stats.Variance(cachedTokens) > 0 {
			row.CachedTokensCorr = stats.SpearmanCorrelation(perToolRunVectors[t], cachedTokens)
		}

		analysisList = append(analysisList, row)
	}
	return analysisList
}

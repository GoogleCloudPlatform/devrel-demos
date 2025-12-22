package runner

import (
	"strings"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/stats"
)

type AltSummary struct {
	Name           string  `json:"name"`
	SuccessRate    float64 `json:"success_rate"`
	AvgDuration    float64 `json:"avg_duration"` // seconds
	AvgTokens      float64 `json:"avg_tokens"`
	AvgLint        float64 `json:"avg_lint"`
	TotalLint      int     `json:"total_lint"`
	Count          int     `json:"count"`
	SuccessCount   int     `json:"success_count"`
	Timeouts       int     `json:"timeouts"`
	TotalToolCalls int     `json:"total_tool_calls"`
	FailedTools    int     `json:"failed_tools"`

	// P-values vs control
	PDuration float64 `json:"p_duration,omitempty"`
	PTokens   float64 `json:"p_tokens,omitempty"`
	PLint     float64 `json:"p_lint,omitempty"`
	PSuccess  float64 `json:"p_success,omitempty"`
	PTimeout  float64 `json:"p_timeout,omitempty"`

	// Raw data for frontend to do its own advanced stats if needed
	Durations      []float64 `json:"durations,omitempty"`
	Tokens         []float64 `json:"tokens,omitempty"`
	Lints          []float64 `json:"lints,omitempty"`
	Passes         []float64 `json:"passes,omitempty"`
	Failures       []float64 `json:"failures,omitempty"`
	AvgTestsPassed float64   `json:"avg_tests_passed"`
	AvgTestsFailed float64   `json:"avg_tests_failed"`
	PTestsPassed   float64   `json:"p_tests_passed,omitempty"`
	PTestsFailed   float64   `json:"p_tests_failed,omitempty"`
}

type ExperimentSummary struct {
	TotalRuns      int                   `json:"total_runs"`
	SuccessfulRuns int                   `json:"successful_runs"`
	SuccessRate    float64               `json:"success_rate"`
	AvgDuration    float64               `json:"avg_duration"` // seconds
	AvgTokens      float64               `json:"avg_tokens"`
	TotalLint      int                   `json:"total_lint"`
	Alternatives   map[string]AltSummary `json:"alternatives"`
}

func CalculateSummary(results []Result, controlAlt string) *ExperimentSummary {
	if len(results) == 0 {
		return &ExperimentSummary{Alternatives: make(map[string]AltSummary)}
	}

	summary := &ExperimentSummary{
		TotalRuns:    len(results),
		Alternatives: make(map[string]AltSummary),
	}

	type intermediate struct {
		totalRuns      int
		successes      int
		timeouts       int
		totalTokens    int64
		totalLint      int
		totalDur       time.Duration
		totalToolCalls int
		failedTools    int
		durations      []float64
		tokens         []float64
		lints          []float64
		passes         []float64
		failures       []float64
	}

	byAlt := make(map[string]*intermediate)
	altNames := []string{}

	for _, res := range results {
		if _, ok := byAlt[res.Alternative]; !ok {
			byAlt[res.Alternative] = &intermediate{}
			altNames = append(altNames, res.Alternative)
		}
		m := byAlt[res.Alternative]
		m.totalRuns++

		if res.IsSuccess {
			m.successes++
			summary.SuccessfulRuns++
			m.totalDur += res.Duration
			m.durations = append(m.durations, res.Duration.Seconds())

			if res.AgentMetrics != nil {
				m.totalTokens += int64(res.AgentMetrics.TotalTokens)
				m.tokens = append(m.tokens, float64(res.AgentMetrics.TotalTokens))
			}
		} else if res.Error != nil && IsTimeout(res.Error) {
			m.timeouts++
		}

		if res.Error == nil && res.AgentMetrics != nil {
			for _, tc := range res.AgentMetrics.ToolCalls {
				m.totalToolCalls++
				if tc.Status != "success" {
					m.failedTools++
				}
			}
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

	for _, name := range altNames {
		m := byAlt[name]
		as := AltSummary{
			Name:           name,
			Count:          m.totalRuns,
			SuccessCount:   m.successes,
			SuccessRate:    float64(m.successes) / float64(m.totalRuns) * 100,
			TotalLint:      m.totalLint,
			Timeouts:       m.timeouts,
			TotalToolCalls: m.totalToolCalls,
			FailedTools:    m.failedTools,
			Durations:      m.durations,
			Tokens:         m.tokens,
			Lints:          m.lints,
			Passes:         m.passes,
			Failures:       m.failures,
		}

		if m.successes > 0 {
			as.AvgDuration = (m.totalDur / time.Duration(m.successes)).Seconds()
			as.AvgTokens = float64(m.totalTokens) / float64(m.successes)

			totalSuccessDur += m.totalDur
			totalSuccessTokens += m.totalTokens
		}
		as.AvgLint = float64(m.totalLint) / float64(m.totalRuns)

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

	if summary.SuccessfulRuns > 0 {
		summary.AvgDuration = (totalSuccessDur / time.Duration(summary.SuccessfulRuns)).Seconds()
		summary.AvgTokens = float64(totalSuccessTokens) / float64(summary.SuccessfulRuns)
	}

	// Stats vs Control
	if controlAlt == "" && len(altNames) > 0 {
		controlAlt = altNames[0]
	}

	if control, ok := summary.Alternatives[controlAlt]; ok {
		for name, as := range summary.Alternatives {
			if name == controlAlt {
				continue
			}

			as.PDuration = stats.WelchTTest(control.Durations, as.Durations)
			as.PTokens = stats.WelchTTest(control.Tokens, as.Tokens)
			as.PLint = stats.WelchTTest(control.Lints, as.Lints)
			as.PSuccess = stats.FisherExactTest(
				control.SuccessCount, control.Count-control.SuccessCount,
				as.SuccessCount, as.Count-as.SuccessCount,
			)
			as.PTimeout = stats.FisherExactTest(
				control.Timeouts, control.Count-control.Timeouts,
				as.Timeouts, as.Count-as.Timeouts,
			)
			as.PTestsPassed = stats.WelchTTest(control.Passes, as.Passes)
			as.PTestsFailed = stats.WelchTTest(control.Failures, as.Failures)
			summary.Alternatives[name] = as
		}
	}

	return summary
}

func IsTimeout(err error) bool {
	if err == nil {
		return false
	}
	msg := strings.ToLower(err.Error())
	return strings.Contains(msg, "timeout") || strings.Contains(msg, "deadline exceeded")
}

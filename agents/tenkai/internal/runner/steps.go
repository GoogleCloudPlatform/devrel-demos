package runner

import (
	"context"
	"strings"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
)

// performValidation checks the output code and runs tests/lints
func (r *Runner) performValidation(ctx context.Context, res *Result, wsPath string, scenConfig interface{}, stdoutContent string) {
	// Determine if we should evaluate
	shouldEvaluate := res.Error == nil
	if res.Error != nil && !strings.Contains(res.Error.Error(), "timeout") {
		// Non-timeout errors might still have partial code worth evaluating
		shouldEvaluate = true
	}

	if !shouldEvaluate {
		return
	}

	// Type assertion for config
	cfg, ok := scenConfig.(*config.ScenarioConfig)
	if !ok {
		// Log warning? For now simply return as we can't validate without rules
		return
	}

	metrics, valReport, err := r.evaluateCode(ctx, wsPath, cfg, stdoutContent)

	if err != nil {
		res.Error = err
		res.ErrorStr = err.Error()
	} else {
		res.EvaluationMetrics = metrics
		if valReport != nil {
			res.IsSuccess = valReport.OverallSuccess
			// Note: We are not setting res.ValidationReport to JSON string here as in original code
		}
	}
}

// loadMetrics updates the result with metrics from DB
func (r *Runner) loadMetrics(res *Result) {
	metrics, err := r.db.GetRunMetrics(res.RunID)
	if err == nil {
		res.AgentMetrics = metrics
	}
}

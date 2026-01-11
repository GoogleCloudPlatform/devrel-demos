package report

import (
	"bytes"
	"strings"
	"testing"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db/models"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/parser"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/runner"
)

func TestReportSignificanceMarkers(t *testing.T) {
	// Mock Results
	results := []runner.Result{}
	// Control: Mean ~10s
	for i := 1; i <= 10; i++ {
		results = append(results, runner.Result{
			Alternative:       "Control",
			Scenario:          "Scen1",
			Repetition:        i,
			Status:            "COMPLETED",
			Duration:          time.Duration(10) * time.Second,
			AgentMetrics:      &parser.AgentMetrics{TotalTokens: 1000},
			EvaluationMetrics: &models.EvaluationMetrics{LintIssues: 5},
		})
	}

	// Significant Alt: Mean 20s (much slower)
	for i := 1; i <= 10; i++ {
		results = append(results, runner.Result{
			Alternative:       "Significant",
			Scenario:          "Scen1",
			Repetition:        i,
			Status:            "COMPLETED",
			Duration:          time.Duration(20) * time.Second,
			AgentMetrics:      &parser.AgentMetrics{TotalTokens: 2000},
			EvaluationMetrics: &models.EvaluationMetrics{LintIssues: 10},
		})
	}

	cfg := &config.Configuration{
		Name:        "Verification Test",
		Repetitions: 10,
		Alternatives: []config.Alternative{
			{Name: "Control"},
			{Name: "Significant"},
		},
	}

	var buf bytes.Buffer
	gen := &EnhancedMarkdownGenerator{
		Results: results,
		Cfg:     cfg,
		w:       &buf,
	}

	err := gen.Generate()
	if err != nil {
		t.Fatalf("Generate failed: %v", err)
	}

	report := buf.String()

	// Verify that we have significance markers (**) for the Significant alternative
	// Welch's t-test for 10s vs 20s with 0 variance should be extremely significant
	if !strings.Contains(report, "**") {
		t.Errorf("Expected highly significant markers (**), but none found in report:\n%s", report)
	}

	// Verify the explanation section exists
	if !strings.Contains(report, "Statistical Analysis Notes") {
		t.Errorf("Expected 'Statistical Analysis Notes' section, but not found")
	}

	if !strings.Contains(report, "Welch's t-test") {
		t.Errorf("Expected explanation of Welch's t-test")
	}
}

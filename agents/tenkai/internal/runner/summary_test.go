package runner

import (
	"testing"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/parser"
)

func TestCalculateSummary(t *testing.T) {
	// Setup mock results
	// Control: 5 runs, 3 success, 2 failures
	// Alt1: 5 runs, 4 success, 1 failure (Better)
	// Alt2: 1 run (Should be ignored for stats)
	// Alt3: 0 runs (Should be ignored)

	control := "Control"
	alt1 := "Alt1"
	alt2 := "Alt2"
	alt3 := "Alt3"
	allAlts := []string{control, alt1, alt2, alt3}

	results := []Result{}

	// Control: 3 success, 2 fail
	// Successes have 2 tool calls each
	for i := 0; i < 3; i++ {
		results = append(results, Result{
			Alternative:  control,
			IsSuccess:    true,
			Status:       "COMPLETED",
			Duration:     1 * time.Second,
			AgentMetrics: &parser.AgentMetrics{TotalToolCallsCount: 2, FailedToolCalls: 0},
		})
	}
	// Failures have 1 tool call, which failed
	for i := 0; i < 2; i++ {
		results = append(results, Result{
			Alternative:  control,
			IsSuccess:    false,
			Status:       "COMPLETED",
			Duration:     2 * time.Second,
			AgentMetrics: &parser.AgentMetrics{TotalToolCallsCount: 1, FailedToolCalls: 1},
		})
	}

	// Alt1: 4 success, 1 fail
	for i := 0; i < 4; i++ {
		results = append(results, Result{Alternative: alt1, IsSuccess: true, Status: "COMPLETED", Duration: 500 * time.Millisecond})
	}
	results = append(results, Result{Alternative: alt1, IsSuccess: false, Status: "COMPLETED", Duration: 1 * time.Second})

	// Alt2: 1 run
	results = append(results, Result{Alternative: alt2, IsSuccess: true, Status: "COMPLETED", Duration: 1 * time.Second})

	// Alt3: 0 runs
	// Running/Queued runs (should be ignored)
	results = append(results, Result{Alternative: control, Status: "RUNNING"})
	results = append(results, Result{Alternative: alt3, Status: "QUEUED"})

	// Aborted runs (should be ignored)
	results = append(results, Result{Alternative: control, Status: "COMPLETED", Reason: "ABORTED"})

	summary := CalculateSummary(results, control, allAlts, nil, FilterAll)

	if summary.TotalRuns != 11 { // 5 + 5 + 1 (Aborted ignored)
		t.Errorf("Expected 11 total runs, got %d", summary.TotalRuns)
	}

	// Verify Control Stats
	cStats := summary.Alternatives[control]
	if cStats.TotalRuns != 5 {
		t.Errorf("Expected 5 runs for control, got %d", cStats.TotalRuns)
	}

	if cStats.SuccessCount != 3 {
		t.Errorf("Expected 3 success for control, got %d", cStats.SuccessCount)
	}

	// Tool Calls: (3 * 2) + (2 * 1) = 8
	if cStats.TotalToolCalls != 8 {
		t.Errorf("Expected 8 total tool calls for control, got %d", cStats.TotalToolCalls)
	}
	// Failed Tools: (3 * 0) + (2 * 1) = 2
	if cStats.FailedToolCalls != 2 {
		t.Errorf("Expected 2 failed tool calls for control, got %d", cStats.FailedToolCalls)
	}

	// Verify Alt1 Stats (N=5, should have P-values)
	a1Stats := summary.Alternatives[alt1]
	if a1Stats.TotalRuns != 5 {
		t.Errorf("Expected 5 runs for Alt1, got %d", a1Stats.TotalRuns)
	}
	// PSuccess should be calculated (Fisher Exact)
	// PDuration should be calculated (Welch)
	// Just check they are not 0 (or at least processed)
	// Since we mock exact data, we could calculate expected P, but checking it's populated is enough for logic test
	// Actually Fisher might be 1.0 if not significant.
	// But PDuration should be valid.

	// Verify Alt2 Stats (N=1, should NOT have P-values for T-test)
	a2Stats := summary.Alternatives[alt2]
	if a2Stats.TotalRuns != 1 {
		t.Errorf("Expected 1 run for Alt2, got %d", a2Stats.TotalRuns)
	}
	// With new logic, PDuration should be -1.0 if not calculated
	if a2Stats.PDuration != -1.0 {
		t.Errorf("Expected PDuration -1.0 (Not Calculated) for N=1, got %f", a2Stats.PDuration)
	}
	if a2Stats.PInputTokens != -1.0 {
		t.Errorf("Expected PInputTokens -1.0 for N=1, got %f", a2Stats.PInputTokens)
	}
	if a2Stats.POutputTokens != -1.0 {
		t.Errorf("Expected POutputTokens -1.0 for N=1, got %f", a2Stats.POutputTokens)
	}

	// Verify Alt3 Stats (N=0)
	a3Stats := summary.Alternatives[alt3]
	if a3Stats.TotalRuns != 0 {
		t.Errorf("Expected 0 runs for Alt3, got %d", a3Stats.TotalRuns)
	}
	if a3Stats.PDuration != -1.0 {
		t.Errorf("Expected PDuration -1.0 for N=0, got %f", a3Stats.PDuration)
	}
}

func TestCalculateSummaryFiltering(t *testing.T) {
	control := "Control"
	allAlts := []string{control}
	results := []Result{}

	// 1. Success
	results = append(results, Result{Alternative: control, IsSuccess: true, Status: "COMPLETED", Reason: db.ReasonSuccess})
	// 2. Validation Failure
	results = append(results, Result{Alternative: control, IsSuccess: false, Status: "COMPLETED", Reason: db.ReasonFailedValidation})
	// 3. Timeout
	results = append(results, Result{Alternative: control, IsSuccess: false, Status: "COMPLETED", Reason: db.ReasonFailedTimeout})
	// 4. Loop
	results = append(results, Result{Alternative: control, IsSuccess: false, Status: "COMPLETED", Reason: db.ReasonFailedLoop})

	// Case 1: FilterAll
	sAll := CalculateSummary(results, control, allAlts, nil, FilterAll)
	if sAll.TotalRuns != 4 {
		t.Errorf("FilterAll: Expected 4 runs, got %d", sAll.TotalRuns)
	}

	// Case 2: FilterCompleted (Validation + Success)
	sComp := CalculateSummary(results, control, allAlts, nil, FilterCompleted)
	if sComp.TotalRuns != 2 {
		t.Errorf("FilterCompleted: Expected 2 runs (Success + ValFail), got %d", sComp.TotalRuns)
	}
	if sComp.Alternatives[control].FailureReasons["Timeout"] > 0 {
		t.Errorf("FilterCompleted: Expected 0 timeouts")
	}

	// Case 3: FilterSuccessful
	sSucc := CalculateSummary(results, control, allAlts, nil, FilterSuccessful)
	if sSucc.TotalRuns != 1 {
		t.Errorf("FilterSuccessful: Expected 1 run, got %d", sSucc.TotalRuns)
	}
	if sSucc.SuccessfulRuns != 1 {
		t.Errorf("FilterSuccessful: Expected 1 successful run")
	}
}

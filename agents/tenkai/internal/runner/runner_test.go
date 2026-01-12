package runner

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db/models"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/workspace"
)

func TestIsTimeout(t *testing.T) {
	tests := []struct {
		name     string
		res      Result
		expected bool
	}{
		{
			name:     "Explicit Timeout Error",
			res:      Result{Error: fmt.Errorf("context deadline exceeded")},
			expected: true,
		},
		{
			name:     "Timeout String Error",
			res:      Result{Error: fmt.Errorf("execution timeout")},
			expected: true,
		},
		{
			name:     "Other Error",
			res:      Result{Error: fmt.Errorf("process failed")},
			expected: false,
		},
		{
			name:     "No Error",
			res:      Result{},
			expected: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := tt.res.IsTimeout(); got != tt.expected {
				t.Errorf("Result.IsTimeout() = %v, want %v", got, tt.expected)
			}
		})
	}
}

func TestEarlyExit(t *testing.T) {
	// 1. Setup Temp Workspace
	tmpDir := t.TempDir()
	scenariosDir := filepath.Join(tmpDir, "scenarios")
	os.MkdirAll(scenariosDir, 0755)

	// Create dummy scenario
	scenName := "early-exit-test"
	scenDir := filepath.Join(scenariosDir, scenName)
	os.MkdirAll(scenDir, 0755)
	// Write scenario.yaml with dummy validation
	yamlContent := `
name: test
task: test
validation:
  - type: command
    command: "true"
    expect_exit_code: 0
`
	os.WriteFile(filepath.Join(scenDir, "scenario.yaml"), []byte(yamlContent), 0644)
	// We rely on PrepareWorkspace generating PROMPT.md from task: test

	// 2. Setup Runner with DB
	wsMgr := workspace.New(tmpDir, scenariosDir, scenariosDir)
	r := New(wsMgr, 1)

	// Setup Test DB
	dbPath := filepath.Join(tmpDir, "tenkai.db")
	testDB, err := db.Open(dbPath)
	if err != nil {
		t.Fatalf("Failed to open test DB: %v", err)
	}
	defer testDB.Close()
	r.SetDB(testDB)

	// Create Experiment in DB
	exp := &models.Experiment{
		Name:      "test-run",
		Timestamp: time.Now(),
		Status:    "RUNNING",
		Reps:      1,
	}
	expID, err := testDB.CreateExperiment(exp)
	if err != nil {
		t.Fatalf("Failed to create experiment: %v", err)
	}
	r.SetExperimentID(expID)

	// 3. Setup Config with "Agent" command
	// We use a bash command that prints result then sleeps
	// The result JSON must match what parser expects
	resultJSON := `{"type": "result", "status": "success", "stats": {"total_tokens": 10}}`
	// Command: echo line, sleep 10. Timeout is 2s.
	// If logic works, it exits before 2s timeout.

	cfg := &config.Configuration{
		Name:          "test-run",
		Repetitions:   1,
		MaxConcurrent: 1,
		Timeout:       "2s",
		Scenarios:     []string{scenDir}, // Use full path or ID? Runner uses filepath.Base(scenPath) as ID
		Alternatives: []config.Alternative{
			{
				Name:    "sleepy-agent",
				Command: "bash",
				Args:    []string{"-c", fmt.Sprintf("echo '%s'; sleep 10", resultJSON)},
			},
		},
	}

	// 4. Run
	start := time.Now()
	results, err := r.Run(context.Background(), cfg, start, filepath.Join(tmpDir, "runs"))

	// 5. Assertions
	if err != nil {
		t.Fatalf("Run failed: %v", err)
	}
	if len(results) != 1 {
		t.Fatalf("Expected 1 result, got %d", len(results))
	}
	res := results[0]

	if res.Error != nil {
		t.Errorf("Expected no error (early exit), got: %v", res.Error)
	}
	if time.Since(start) > 6*time.Second {
		t.Errorf("Test took too long, early exit didn't trigger")
	}
	if res.Status != "COMPLETED" { // db.RunStatusCompleted
		t.Errorf("Expected status COMPLETED, got %s", res.Status)
	}
}

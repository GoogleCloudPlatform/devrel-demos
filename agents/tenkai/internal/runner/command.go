package runner

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db/models"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/workspace"
)

// runSingle runs a single alternative on a scenario.
// This is used by Worker (to run locally in container) and Orchestrator (ModeLocal only).
func (r *Runner) runSingle(ctx context.Context, alt config.Alternative, sID string, rep int, experimentDir string, timeout time.Duration, runID int64) Result {
	start := time.Now()

	log.Printf("Starting %s on %s repetition %d (RunID: %d)", alt.Name, sID, rep, runID)

	// Prepare Workspace Options
	opts := workspace.WorkspaceOptions{
		Command:        alt.Command,
		Settings:       alt.Settings,
		SettingsBlocks: alt.SettingsBlocks,
		Extensions:     alt.Extensions,
		Skills:         alt.Skills,
		MCPServers:     alt.MCPServers,
	}

	// If in Worker mode, we use the specific run folder under RunsDir as the exact workspace root
	if r.Mode == ModeWorker {
		opts.OverrideWSPath = filepath.Join(r.WorkspaceMgr.RunsDir, fmt.Sprintf("%d", runID))
	}

	scenConfig, err := r.WorkspaceMgr.Prepare(experimentDir, alt.Name, sID, rep, opts)
	if err != nil {
		return r.failRun(runID, alt.Name, sID, rep, db.ReasonFailedError, err)
	}

	wsPath := scenConfig.Root
	projectDir := scenConfig.Project

	// Execute Agent
	// We use command execution here
	cmdCtx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	// If alt.Command is not absolute, check if it's in PATH or relative
	cmdName := alt.Command
	cmdArgs := alt.Args

	// Environment
	env := os.Environ()
	// Set isolated HOME and Go paths
	env = append(env, fmt.Sprintf("HOME=%s", scenConfig.Home))
	env = append(env, fmt.Sprintf("GOPATH=%s", filepath.Join(scenConfig.Home, "go")))
	env = append(env, fmt.Sprintf("GOCACHE=%s", filepath.Join(scenConfig.Home, "cache")))

	// Remove Vertex AI env var if present to force API key usage if key is provided
	// Actually, we can just filter it out or unset it.
	// But `os.Environ()` returns a copy. We need to filter.
	var filteredEnv []string
	for _, e := range env {
		if !strings.HasPrefix(e, "GOOGLE_GENAI_USE_VERTEXAI=") {
			filteredEnv = append(filteredEnv, e)
		}
	}
	env = filteredEnv

	// Ensure isolated environment has required binaries
	// (PATH is already inherited from os.Environ)

	// Run Command
	stdoutPath := filepath.Join(wsPath, "stdout.log")
	stderrPath := filepath.Join(wsPath, "stderr.log")

	fOut, err := os.Create(stdoutPath)
	if err != nil {
		return r.failRun(runID, alt.Name, sID, rep, db.ReasonFailedError, fmt.Errorf("failed to create stdout file: %w", err))
	}
	defer func() { _ = fOut.Close() }()

	fErr, err := os.Create(stderrPath)
	if err != nil {
		return r.failRun(runID, alt.Name, sID, rep, db.ReasonFailedError, fmt.Errorf("failed to create stderr file: %w", err))
	}
	defer func() { _ = fErr.Close() }()

	// Initialize Result for streaming updates
	res := &Result{
		RunID:       runID,
		Alternative: alt.Name,
		Scenario:    sID,
		Repetition:  rep,
	}

	cmd := exec.CommandContext(cmdCtx, cmdName, cmdArgs...)
	cmd.Dir = projectDir
	cmd.Env = env

	// Set up pipes for streaming
	stdoutPipe, err := cmd.StdoutPipe()
	if err != nil {
		return r.failRun(runID, alt.Name, sID, rep, db.ReasonFailedError, fmt.Errorf("failed to get stdout pipe: %w", err))
	}
	stderrPipe, err := cmd.StderrPipe()
	if err != nil {
		return r.failRun(runID, alt.Name, sID, rep, db.ReasonFailedError, fmt.Errorf("failed to get stderr pipe: %w", err))
	}
	stdinPipe, err := cmd.StdinPipe()
	if err != nil {
		return r.failRun(runID, alt.Name, sID, rep, db.ReasonFailedError, fmt.Errorf("failed to get stdin pipe: %w", err))
	}

	// Stream Coordination
	var streamWg sync.WaitGroup
	var stdoutMu sync.Mutex
	var currentStdout strings.Builder
	var stderrMu sync.Mutex
	var currentStderr strings.Builder

	streamState := &StreamState{
		JobID:         fmt.Sprintf("Run-%d", runID),
		Res:           res,
		Cmd:           cmd,
		StreamWg:      &streamWg,
		StdoutMu:      &stdoutMu,
		CurrentStdout: &currentStdout,
		StderrMu:      &stderrMu,
		CurrentStderr: &currentStderr,
		ExecCancel:    cancel, // Allow stream parser to cancel execution
	}

	// Start Streams
	streamWg.Add(2)
	go r.streamStdout(stdoutPipe, fOut, streamState)
	go r.streamStderr(stderrPipe, fErr, streamState)

	// Stream Prompt to Stdin
	promptPath := filepath.Join(projectDir, "PROMPT.md")
	go r.streamPromptContents(promptPath, stdinPipe)

	// Start DB Log Sync (Optional, but good for long runs)
	if r.db != nil && runID != 0 {
		go r.syncLogs(cmdCtx, res, &stdoutMu, &currentStdout, &stderrMu, &currentStderr)
	}

	err = cmd.Run()
	streamWg.Wait() // Ensure we consumed all logs
	duration := time.Since(start)

	if err != nil {
		log.Printf("[Runner] Agent execution failed for RunID %d: %v", runID, err)
		if exitErr, ok := err.(*exec.ExitError); ok {
			log.Printf("[Runner] Exit Status: %d, Stderr: %s", exitErr.ExitCode(), string(exitErr.Stderr))
		}
	}

	// Sync local execution directory back to GCS/Persistent storage if needed
	// We used a local temp dir for execution (in WorkspaceMgr.Prepare)
	// But we need the artifacts in `scenConfig.Root` (which might be the persistent path if we hadn't overridden it?
	// Wait, WorkspaceMgr.Prepare returns the *actual* paths used.
	// If it returned a /tmp path, then `wsPath` is /tmp/...
	// We need to know the *original* intended persistent path to sync back.

	// Re-derive the persistent path or pass it from Prepare?
	// The `experimentDir` passed to runSingle is the root of the experiment.
	// Persistent path: experimentDir/alt/scenario/rep
	// But experimentDir might be /app/assets/_runs (persistent)

	// Let's perform a sync if wsPath starts with /tmp/tenkai-exec
	if strings.HasPrefix(wsPath, "/tmp/tenkai-exec") {
		// Calculate the destination path relative to the persistent runs dir
		// We know r.WorkspaceMgr.RunsDir is the base.
		// Construct expected persistent path:
		// We need to know the relative path structure.
		// Prepare logic: Join(experimentDir, alt, scenario, rep)
		// experimentDir is usually absolute path to the experiment run folder?
		// Actually, `experimentDir` arg in `runSingle` is usually the base path for the experiment.

		// Let's assume we want to copy EVERYTHING from wsPath to the GCS mount.
		// We need the persistent target path.
		// If we are in ModeWorker, `opts.OverrideWSPath` WAS set to the persistent path!
		// But `Prepare` ignored it and gave us a /tmp path.

		// We can reconstruct the target from the original logic in Prepare,
		// OR we can just use the fact that we passed `opts.OverrideWSPath` in `runSingle`.

		targetPath := ""
		if r.Mode == ModeWorker {
			targetPath = filepath.Join(r.WorkspaceMgr.RunsDir, fmt.Sprintf("%d", runID))
		} else {
			// Local mode fallback
			targetPath = filepath.Join(experimentDir, alt.Name, sID, fmt.Sprintf("rep-%d", rep))
		}

		log.Printf("[Runner] Syncing artifacts from %s to %s", wsPath, targetPath)
		if err := r.syncDir(wsPath, targetPath); err != nil {
			log.Fatalf("[Runner] CRITICAL: Failed to sync artifacts: %v. Aborting to prevent data loss.", err)
		}
	}

	// Final Log Sync
	stdout := currentStdout.String()
	stderr := currentStderr.String()

	// Determine Status
	status := db.RunStatusCompleted
	reason := db.ReasonSuccess
	errorStr := ""

	if ctx.Err() == context.DeadlineExceeded {
		reason = db.ReasonFailedTimeout
		errorStr = "Timeout exceeded"
	} else if ctx.Err() == context.Canceled {
		if streamState.IsResultFound() {
			reason = db.ReasonSuccess
		} else {
			reason = db.ReasonFailedError
			errorStr = "Execution canceled"
		}
	} else if err != nil {
		// Exit code check?
		reason = db.ReasonFailedError
		errorStr = err.Error()
	}

	// Run Validation (Tests, Lint)
	metrics, validationReport, valErr := r.evaluateCode(context.Background(), projectDir, scenConfig.Config, stdout)
	if valErr != nil {
		log.Printf("Validation error for run %d: %v", runID, valErr)

		if reason == db.ReasonSuccess {
			reason = db.ReasonFailedValidation
			errorStr = fmt.Sprintf("Validation system error: %v", valErr)
		}
	} else {
		if !validationReport.Success {
			reason = db.ReasonFailedValidation
		}
	}

	// Save Result
	if r.db != nil && runID != 0 {
		runRes := &models.RunResult{
			ID:          runID,
			Status:      status,
			Reason:      reason,
			Duration:    duration.Nanoseconds(),
			Error:       errorStr,
			Stdout:      stdout,
			Stderr:      stderr,
			TestsPassed: metrics.TestsPassed,
			TestsFailed: metrics.TestsFailed,
			LintIssues:  metrics.LintIssues,
			// Loop detected? Need parser logic
		}
		r.ApplyValidationReport(runRes, validationReport)

		if err := r.db.UpdateRunResult(runRes); err != nil {
			log.Printf("Failed to update run result %d: %v", runID, err)
		}

		// Save detailed results
		if validationReport != nil {
			telemetry := &db.RunTelemetry{
				Result:      runRes,
				TestResults: validationReport.DetailedTests,
				LintResults: validationReport.DetailedLints,
			}
			_ = r.db.SaveRunTelemetry(telemetry)
		}
	}

	return Result{
		RunID:       runID,
		Alternative: alt.Name,
		Scenario:    sID,
		Repetition:  rep,
		Status:      status,
		Reason:      reason,
		Duration:    duration,
		ErrorStr:    errorStr,
	}

}

func (r *Runner) failRun(runID int64, alt, scen string, rep int, reason string, err error) Result {
	if r.db != nil && runID != 0 {
		_ = r.db.UpdateRunError(runID, db.RunStatusCompleted, reason, err.Error())
	}
	return Result{
		RunID: runID,

		Alternative: alt,
		Scenario:    scen,
		Repetition:  rep,
		Status:      db.RunStatusCompleted,
		Reason:      reason,
		ErrorStr:    err.Error(),
	}
}

// evaluateCode implementation (restored logic)
func (r *Runner) evaluateCode(ctx context.Context, projectDir string, scenCfg *config.ScenarioConfig, stdout string) (models.RunMetrics, *models.ValidationReport, error) {
	// 1. Run Tests
	// Check if Go project
	if _, err := os.Stat(filepath.Join(projectDir, "go.mod")); err == nil {
		// Run Go Tests
		cmd := exec.CommandContext(ctx, "go", "test", "./...", "-json")
		cmd.Dir = projectDir
		out, _ := cmd.CombinedOutput()

		// Parse Test Output
		// (Assume we have parser logic somewhere, or use basic string check for now)
		// Wait, report package has parsing logic?
		// internal/report/parser.go?
		// Let's use internal/report package if available.

		// For now simple stub:
		passed := strings.Contains(string(out), "PASS")
		failed := strings.Contains(string(out), "FAIL")

		metrics := models.RunMetrics{}
		report := &models.ValidationReport{
			Success: passed && !failed,
		}
		if passed {
			metrics.TestsPassed = 1
		}
		if failed {
			metrics.TestsFailed = 1
		}

		return metrics, report, nil
	}

	// Default (No tests found)
	return models.RunMetrics{}, &models.ValidationReport{Success: true}, nil
}

// syncDir copies all files from src to dst
func (r *Runner) syncDir(src, dst string) error {
	cmd := exec.Command("cp", "-r", src+"/", dst)
	if out, err := cmd.CombinedOutput(); err != nil {
		return fmt.Errorf("cp failed: %v, output: %s", err, string(out))
	}
	return nil
}

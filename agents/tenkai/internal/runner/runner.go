package runner

import (
	"context"
	"fmt"
	"io/fs"
	"log"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db/models"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/parser"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/storage"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/workspace"
)

// Result represents the outcome of a single experiment run.
type Result struct {
	RunID       int64         `json:"run_id"` // DB ID
	Alternative string        `json:"alternative"`
	Scenario    string        `json:"scenario"`
	Repetition  int           `json:"repetition"`
	Duration    time.Duration `json:"duration"`
	Workspace   string        `json:"workspace"`
	Stdout      string        `json:"stdout"`
	Stderr      string        `json:"stderr"`
	Error       error         `json:"-"` // Don't marshal interface
	ErrorStr    string        `json:"error,omitempty"`

	AgentMetrics      *parser.AgentMetrics      `json:"agent_metrics,omitempty"`
	EvaluationMetrics *models.EvaluationMetrics `json:"evaluation_metrics,omitempty"`
	IsSuccess         bool                      `json:"is_success"`
	ValidationReport  string                    `json:"validation_report"`
	Status            string                    `json:"status"` // QUEUED, RUNNING, COMPLETED, ABORTED
	Reason            string                    `json:"reason"` // SUCCESS, FAILURE, TIMEOUT, LOOP, ERROR
}

// IsTimeout returns true if the error associated with this result is a timeout.
func (r Result) IsTimeout() bool {
	if r.Error == nil {
		return false
	}
	msg := strings.ToLower(r.Error.Error())
	return strings.Contains(msg, "timeout") || strings.Contains(msg, "deadline exceeded")
}

// IsTimeoutErr is a utility function to check if a generic error is a timeout.
func IsTimeoutErr(err error) bool {
	if err == nil {
		return false
	}
	msg := strings.ToLower(err.Error())
	return strings.Contains(msg, "timeout") || strings.Contains(msg, "deadline exceeded")
}

type RunnerMode string

const (
	ModeServer RunnerMode = "server" // Orchestrates, queues jobs, but runs nothing locally (unless forced)
	ModeWorker RunnerMode = "worker" // Polls and executes jobs
	ModeLocal  RunnerMode = "local"  // Orchestrates AND runs locally (Backward compatibility)
)

// Runner handles the execution of experiments.
type Runner struct {
	WorkspaceMgr  *workspace.Manager
	MaxConcurrent int
	db            *db.DB
	experimentID  int64
	Storage       storage.ArtifactStorage
	Mode          RunnerMode
}

// New creates a new Runner.
func New(wsMgr *workspace.Manager, maxConcurrent int) *Runner {
	if maxConcurrent < 1 {
		maxConcurrent = 1
	}
	// Hard limit concurrency to GOMAXPROCS to avoid overloading system
	numCPU := runtime.GOMAXPROCS(0)
	if maxConcurrent > numCPU {
		log.Printf("Capping concurrency from %d to GOMAXPROCS (%d)", maxConcurrent, numCPU)
		maxConcurrent = numCPU
	}

	return &Runner{
		WorkspaceMgr:  wsMgr,
		MaxConcurrent: maxConcurrent,
		Mode:          ModeLocal, // Default
	}
}

func (r *Runner) SetDB(d *db.DB) {
	r.db = d
}

func (r *Runner) SetExperimentID(id int64) {
	r.experimentID = id
}

func (r *Runner) SetStorage(s storage.ArtifactStorage) {
	r.Storage = s
}
func (r *Runner) SetMode(m RunnerMode) {
	r.Mode = m
}

// Checkpoint represents the current progress of an experiment.
type Checkpoint struct {
	TotalJobs     int     `json:"total_jobs"`
	CompletedJobs int     `json:"completed_jobs"`
	Percentage    float64 `json:"percentage"`
	LastUpdate    string  `json:"last_update"`
	Status        string  `json:"status"`
}

// DetermineRunStatus calculates the final Status and Reason for a result.
func (r *Runner) DetermineRunStatus(res *Result) (string, string) {
	status := db.RunStatusCompleted
	var reason string

	switch {
	case res.IsSuccess:
		reason = db.ReasonSuccess
	case res.AgentMetrics != nil && res.AgentMetrics.LoopDetected:
		reason = db.ReasonFailedLoop
	case res.ErrorStr != "" && IsTimeoutErr(res.Error):
		reason = db.ReasonFailedTimeout
	case res.ValidationReport != "":
		reason = db.ReasonFailedValidation
	default:
		reason = db.ReasonFailedError
	}
	return status, reason
}

// Run executes the experiments defined in the configuration.

func (r *Runner) Run(ctx context.Context, cfg *config.Configuration, timestamp time.Time, experimentDir string) ([]Result, error) {
	// If in Server mode, we only queue jobs and wait for completion (polling DB status).
	// If in Local mode, we queue assignments and execute them.

	var results []Result
	resultsLimit := cfg.Repetitions * len(cfg.Alternatives) * len(cfg.Scenarios)
	resultsChan := make(chan Result, resultsLimit)

	// 0. Initial checkpoint
	if r.db == nil || r.experimentID == 0 {
		return nil, fmt.Errorf("runner requires valid DB and experiment ID")
	}

	// Ensure logs directory exists (for local orchestrator logs)
	logsDir := filepath.Join(experimentDir, "logs")
	if err := os.MkdirAll(logsDir, 0755); err != nil {
		return nil, fmt.Errorf("failed to create logs dir: %w", err)
	}

	sem := make(chan struct{}, r.MaxConcurrent)
	var wg sync.WaitGroup

	// Wrap context with cancellation for stopping
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()

	// Parse timeout from config
	defaultTimeout := 5 * time.Minute
	timeout := defaultTimeout
	if cfg.Timeout != "" {
		if d, err := time.ParseDuration(cfg.Timeout); err == nil {
			timeout = d
		} else {
			log.Printf("Warning: invalid timeout %q, using default %v", cfg.Timeout, defaultTimeout)
		}
	}

	rc := &runContext{
		Ctx:             ctx,
		ExperimentDir:   experimentDir,
		Timeout:         timeout,
		Timestamp:       timestamp,
		ExperiementName: cfg.Name,
		ResultsChan:     resultsChan,
		Wg:              &wg,
		Sem:             sem,
	}

	r.DispatchAll(rc, cfg)

	if r.Mode == ModeServer {
		// Server Mode: Poll DB for completion instead of waiting for local goroutines
		go func() {
			r.pollDatabaseForCompletion(ctx, resultsLimit, resultsChan)
			close(resultsChan)
		}()
	} else {
		// Local Mode: Wait for goroutines
		go func() {
			wg.Wait()
			close(resultsChan)
		}()
	}

	completed := 0
	for {
		select {
		case res, ok := <-resultsChan:
			if !ok {
				// All current jobs finished or stopped.
				// Final status update for the experiment
				finalStatus := db.ExperimentStatusCompleted
				if len(results) < resultsLimit {
					finalStatus = db.ExperimentStatusAborted
				}
				r.db.UpdateExperimentStatus(r.experimentID, finalStatus)
				goto Done
			}
			completed++

			// Refine Reason and Status before appending to results slice
			res.Status, res.Reason = r.DetermineRunStatus(&res)

			percentage := float64(completed) / float64(resultsLimit) * 100
			log.Printf("Progress: %d/%d jobs completed (%.1f%%)", completed, resultsLimit, percentage)

			savedToDB := false

			runRes := &models.RunResult{
				ID:               res.RunID,
				ExperimentID:     r.experimentID,
				Alternative:      res.Alternative,
				Scenario:         res.Scenario,
				Repetition:       res.Repetition,
				Duration:         int64(res.Duration),
				Error:            res.ErrorStr,
				Stdout:           res.Stdout,
				Stderr:           res.Stderr,
				Status:           res.Status,
				Reason:           res.Reason,
				IsSuccess:        res.IsSuccess,
				ValidationReport: res.ValidationReport,
			}
			if res.EvaluationMetrics != nil {
				runRes.TestsPassed = res.EvaluationMetrics.TestsPassed
				runRes.TestsFailed = res.EvaluationMetrics.TestsFailed
				runRes.LintIssues = res.EvaluationMetrics.LintIssues
			}

			// Use in-memory metrics directly (avoiding DB read-after-write race)
			if res.AgentMetrics != nil {
				runRes.TotalTokens = res.AgentMetrics.TotalTokens
				runRes.InputTokens = res.AgentMetrics.InputTokens
				runRes.OutputTokens = res.AgentMetrics.OutputTokens
				runRes.ToolCallsCount = res.AgentMetrics.TotalToolCallsCount
				runRes.FailedToolCalls = res.AgentMetrics.FailedToolCalls
				runRes.LoopDetected = res.AgentMetrics.LoopDetected
				runRes.CachedTokens = res.AgentMetrics.CachedTokens
				runRes.SessionID = res.AgentMetrics.SessionID
				runRes.Model = res.AgentMetrics.ModelName
				runRes.ModelDuration = res.AgentMetrics.ModelDuration
			}

			// Build Telemetry for Final Save
			telemetry := &db.RunTelemetry{
				Result: runRes,
			}

			if res.AgentMetrics != nil {
				// Evaluation Details
				if res.EvaluationMetrics != nil {
					telemetry.TestResults = res.EvaluationMetrics.Tests
					telemetry.LintResults = res.EvaluationMetrics.Lints
				}
			}
			// Transactional Save with Retry
			var saveErr error
			delay := 100 * time.Millisecond
			for attempt := 0; attempt < 5; attempt++ {
				if err := r.db.SaveRunTelemetry(telemetry); err == nil {
					savedToDB = true
					break
				} else {
					saveErr = err
					log.Printf("Warning: failed to save final run telemetry (attempt %d/5): %v. Retrying...", attempt+1, err)
					time.Sleep(delay)
					delay *= 2
				}
			}
			if !savedToDB {
				return results, fmt.Errorf("failed to save run telemetry after retries (RunID %d): %w", res.RunID, saveErr)
			}

			results = append(results, res)

		case <-time.After(1 * time.Second):

			// Periodically check for STOP signal from DB to cancel context
			action := r.checkAction()
			if action == "stop" {
				log.Printf("[Runner] Received STOP signal for Experiment %d. Canceling context...", r.experimentID)
				cancel()
				// Drain channel
				for range resultsChan {
				}
				goto Done
			}
		}
	}
Done:
	// Final checkpoint
	finalStatus := db.ExperimentStatusCompleted
	if r.checkAction() == "stop" || ctx.Err() != nil {
		finalStatus = db.ExperimentStatusAborted // Use consistent status
	}
	r.db.UpdateExperimentStatus(r.experimentID, finalStatus)

	return results, nil
}

func (r *Runner) checkAction() string {

	exp, err := r.db.GetExperimentByID(r.experimentID)
	if err != nil {
		log.Printf("Warning: failed to get experiment from DB for ID %d: %v", r.experimentID, err)
		return ""
	}

	if exp.ExecutionControl != "" {
		log.Printf("[Runner] checkAction: ID=%d, Control=%s", r.experimentID, exp.ExecutionControl)
	}
	return exp.ExecutionControl
}

// RunJob executes a single job (Run) fetched from the DB.
// This is used by the Worker.
func (r *Runner) RunJob(ctx context.Context, runID int64) error {
	// 1. Fetch Run Details
	run, err := r.db.GetRunResultByID(runID) // We need this method in DB
	if err != nil {
		return fmt.Errorf("failed to fetch run %d: %w", runID, err)
	}

	// 2. Fetch Experiment Config
	exp, err := r.db.GetExperimentByID(run.ExperimentID)
	if err != nil {
		return fmt.Errorf("failed to fetch experiment %d: %w", run.ExperimentID, err)
	}

	// 3. Reconstruct Config/Alternative provided in the run
	// This is tricky because `runSingle` expects `config.Alternative` and `Scenario`.
	// The RunResult has the names. We need to look them up in the Experiment Config.
	// We stored ConfigContent in valid experiments.
	cfg, err := config.Parse([]byte(exp.ConfigContent))
	if err != nil {
		return fmt.Errorf("failed to parse experiment config: %w", err)
	}

	var alt config.Alternative
	found := false
	for _, a := range cfg.Alternatives {
		if a.Name == run.Alternative {
			alt = a
			found = true
			break
		}
	}
	if !found {
		return fmt.Errorf("alternative %s not found in config", run.Alternative)
	}

	// 4. Update Status to RUNNING (handled inside RunJob logic or before?)
	// Worker should do it.

	// 5. Execute
	// We use runSingle but we need to adapt arguments.
	// existing runSingle signature:
	// func (r *Runner) runSingle(ctx context.Context, alt config.Alternative, scenarioID string, rep int, experimentDir string, timeout time.Duration, runID int64) Result

	// ExperimentDir: we might need to recreate it or use a temp dir for Worker.
	// Workers rely on ephemeral workspace.
	// We need actual absolute path.
	cwd, _ := os.Getwd()
	baseDir := cwd
	if os.Getenv("MODE") == "worker" || os.Getenv("K_SERVICE") != "" || os.Getenv("CLOUD_RUN_JOB") != "" {
		baseDir = os.TempDir()
	}
	workerExpDir := filepath.Join(baseDir, "worker_runs", fmt.Sprintf("%d", run.ID))
	if err := os.MkdirAll(workerExpDir, 0755); err != nil {
		return fmt.Errorf("failed to create worker run dir %s: %w", workerExpDir, err)
	}

	timeout := 10 * time.Minute
	if cfg.Timeout != "" {
		if d, err := time.ParseDuration(cfg.Timeout); err == nil {
			timeout = d
		}
	}

	res := r.runSingle(ctx, alt, run.Scenario, run.Repetition, workerExpDir, timeout, runID)

	// Persist Result to DB (Critical for Worker Mode)
	// Mirroring logic from Run() loop
	res.Status, res.Reason = r.DetermineRunStatus(&res)

	// Prepare RunResult for persistence
	runRes := &models.RunResult{
		ID:               res.RunID,
		ExperimentID:     run.ExperimentID, // Use original experiment ID
		Alternative:      res.Alternative,
		Scenario:         res.Scenario,
		Repetition:       res.Repetition,
		Duration:         int64(res.Duration),
		Error:            res.ErrorStr,
		Stdout:           res.Stdout,
		Stderr:           res.Stderr,
		Status:           res.Status,
		Reason:           res.Reason,
		IsSuccess:        res.IsSuccess,
		ValidationReport: res.ValidationReport,
	}

	if res.EvaluationMetrics != nil {
		runRes.TestsPassed = res.EvaluationMetrics.TestsPassed
		runRes.TestsFailed = res.EvaluationMetrics.TestsFailed
		runRes.LintIssues = res.EvaluationMetrics.LintIssues
	}

	// Use in-memory metrics directly
	if res.AgentMetrics != nil {
		runRes.TotalTokens = res.AgentMetrics.TotalTokens
		runRes.InputTokens = res.AgentMetrics.InputTokens
		runRes.OutputTokens = res.AgentMetrics.OutputTokens
		runRes.ToolCallsCount = res.AgentMetrics.TotalToolCallsCount
		runRes.FailedToolCalls = res.AgentMetrics.FailedToolCalls
		runRes.LoopDetected = res.AgentMetrics.LoopDetected
		runRes.CachedTokens = res.AgentMetrics.CachedTokens
		runRes.SessionID = res.AgentMetrics.SessionID
		runRes.Model = res.AgentMetrics.ModelName
		runRes.ModelDuration = res.AgentMetrics.ModelDuration
	}

	telemetry := &db.RunTelemetry{
		Result: runRes,
	}

	if res.EvaluationMetrics != nil {
		telemetry.TestResults = res.EvaluationMetrics.Tests
		telemetry.LintResults = res.EvaluationMetrics.Lints
	}

	if err := r.db.SaveRunTelemetry(telemetry); err != nil {
		return fmt.Errorf("failed to save run telemetry: %w", err)
	}

	if res.ErrorStr != "" {
		return fmt.Errorf("job failed: %s", res.ErrorStr)
	}
	return nil
}

func (r *Runner) runSingle(ctx context.Context, alt config.Alternative, scenarioID string, rep int, experimentDir string, timeout time.Duration, runID int64) Result {
	start := time.Now()

	res := Result{
		RunID:       runID,
		Alternative: alt.Name,
		Scenario:    scenarioID,
		Repetition:  rep,
	}

	// Calculate a job ID for logging
	jobID := fmt.Sprintf("[%s|%s|#%d]", alt.Name, scenarioID, rep)
	log.Printf("START %s", jobID)

	// Ensure paths are absolute before passing to WorkspaceMgr
	// 1. Prepare Workspace
	wsInfo, err := r.prepareWorkspaceForRun(experimentDir, alt, scenarioID, rep)
	if err != nil {
		res.Error = fmt.Errorf("workspace prep failed: %w", err)
		res.ErrorStr = res.Error.Error()
		return res
	}
	res.Workspace = wsInfo.Project

	// Anchor the workspace to prevent Gemini from walking up to tenkai root
	// If isolation is needed, we should rely on the agent creating it or the scenario template providing it.
	// 2. Prepare Command
	cmd, jobCtx, jobCancel, _, execCancel, err := r.createCommand(ctx, alt, wsInfo, timeout, jobID)
	if err != nil {
		// Should not happen with current logic, but handle it
		res.Error = fmt.Errorf("command creation failed: %w", err)
		res.ErrorStr = res.Error.Error()
		return res
	}
	defer jobCancel()
	defer execCancel()

	// 3. Capture Output (Real-time Stream)
	logFile, stderrFile, logPath, err := r.setupLogFiles(wsInfo, alt.Name, scenarioID, rep)
	if err != nil {
		res.Error = err
		res.ErrorStr = res.Error.Error()
		return res
	}
	defer logFile.Close()
	defer stderrFile.Close()

	stdoutPipe, err := cmd.StdoutPipe()
	if err != nil {
		res.Error = fmt.Errorf("failed to create stdout pipe: %w", err)
		res.ErrorStr = res.Error.Error()
		return res
	}

	stderrPipe, err := cmd.StderrPipe()
	if err != nil {
		res.Error = fmt.Errorf("failed to create stderr pipe: %w", err)
		res.ErrorStr = res.Error.Error()
		return res
	}

	stdinPipe, err := cmd.StdinPipe()
	if err != nil {
		res.Error = fmt.Errorf("failed to create stdin pipe: %w", err)
		res.ErrorStr = res.Error.Error()
		return res
	}

	// 3. Open PROMPT.md for Stdin
	promptPath := filepath.Join(wsInfo.Project, "PROMPT.md")
	// Use helper for prompt streaming
	go r.streamPromptContents(promptPath, stdinPipe)

	var streamWg sync.WaitGroup
	streamWg.Add(2)

	// Context for raw log batching
	syncCtx, syncCancel := context.WithCancel(jobCtx)
	defer syncCancel()

	// RAW LOG SYNC (Batched every 1s)
	var stdoutMu, stderrMu sync.Mutex
	var currentStdout, currentStderr strings.Builder

	ss := &StreamState{
		JobID:         jobID,
		Res:           &res,
		Cmd:           cmd,
		StreamWg:      &streamWg,
		StdoutMu:      &stdoutMu,
		CurrentStdout: &currentStdout,
		StderrMu:      &stderrMu,
		CurrentStderr: &currentStderr,
		ExecCancel:    execCancel,
	}

	if res.RunID != 0 {
		go r.syncLogs(syncCtx, &res, &stdoutMu, &currentStdout, &stderrMu, &currentStderr)
	}
	// STDOUT STREAMER
	go r.streamStdout(stdoutPipe, logFile, ss)

	// STDERR STREAMER
	go r.streamStderr(stderrPipe, stderrFile, ss)

	// RESET TIMER: Exclude workspace setup and asset download time
	start = time.Now()

	if err := cmd.Start(); err != nil {
		res.Error = fmt.Errorf("execution failed to start: %w", err)
		res.ErrorStr = res.Error.Error()
		return res
	}

	// Wait for streams and command
	waitErr := r.waitForCommand(cmd, ss, jobCtx, timeout)
	if waitErr != nil {
		res.Error = waitErr
		res.ErrorStr = res.Error.Error()
	} else {
		res.Error = nil
		res.ErrorStr = ""
	}

	res.Duration = time.Since(start)

	// Final raw log sync
	if r.db != nil && res.RunID != 0 {
		r.db.UpdateRunLogs(res.RunID, currentStdout.String(), currentStderr.String())
	}

	res.Stdout = currentStdout.String()
	res.Stderr = currentStderr.String()

	// 4. Metrics are already populated in res.AgentMetrics by streamStdout
	if res.AgentMetrics == nil {
		res.AgentMetrics = &parser.AgentMetrics{}
	}
	// 5. Verify Code (Test & Lint) - skip for timeouts and loops since code is incomplete
	shouldEvaluate := res.Error == nil
	if res.AgentMetrics != nil && res.AgentMetrics.LoopDetected {
		shouldEvaluate = false
	}
	if res.Error != nil && (strings.Contains(res.Error.Error(), "timeout") || strings.Contains(res.Error.Error(), "deadline exceeded")) {
		shouldEvaluate = false
	}

	if shouldEvaluate {
		// Use the configuration passed from Manager (in-memory)
		scenConfig := wsInfo.Config

		// Read the metrics log to get stdout content for validation
		logContentBytes, _ := os.ReadFile(logPath)
		stdoutContent := string(logContentBytes)

		metrics, valReport, err := r.evaluateCode(jobCtx, wsInfo.Project, scenConfig, stdoutContent)

		if err != nil {
			log.Printf("Evaluation failed: %v", err)
			res.Error = err
			res.ErrorStr = err.Error()
		} else {
			res.EvaluationMetrics = metrics
			if valReport != nil {
				// We need a dummy RunResult to use ApplyValidationReport
				dummy := &models.RunResult{}
				r.ApplyValidationReport(dummy, valReport)

				res.IsSuccess = dummy.IsSuccess
				res.Reason = dummy.Reason
				res.ValidationReport = dummy.ValidationReport

				// Update metrics counts
				if res.EvaluationMetrics == nil {
					res.EvaluationMetrics = &models.EvaluationMetrics{}
				}
				res.EvaluationMetrics.TestsPassed = valReport.TestsPassed
				res.EvaluationMetrics.TestsFailed = valReport.TestsFailed
				res.EvaluationMetrics.LintIssues = valReport.LintIssues
			}
		}
	}

	// 6. Archive Workspace Artifacts
	if r.Storage != nil && res.RunID != 0 {
		if err := r.archiveArtifacts(ctx, res.RunID, wsInfo.Project); err != nil {
			log.Printf("Warning: failed to archive artifacts for run %d: %v", res.RunID, err)
			// Don't fail the run for this
		}
	}

	// Finalize IsSuccess using centralized logic
	if res.Error != nil {
		res.IsSuccess = false
	}
	// res.IsSuccess is already set by Validation/EarlyExit logic

	// Ensure live monitor is stopped before returning to avoid race conditions on DB
	jobCancel()

	log.Printf("DONE  %s in %s", jobID, res.Duration.Round(time.Millisecond))

	// Result will be saved to DB in the main Run loop
	return res
}

func (r *Runner) archiveArtifacts(ctx context.Context, runID int64, wsPath string) error {
	return filepath.WalkDir(wsPath, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			if d.Name() == ".git" || d.Name() == "node_modules" || d.Name() == ".gemini" {
				return filepath.SkipDir
			}
			return nil
		}

		relPath, err := filepath.Rel(wsPath, path)
		if err != nil {
			return err
		}
		if relPath == "." || relPath == "PROMPT.md" || relPath == "GEMINI.md" || relPath == "settings.json" || relPath == "system_prompt.md" {
			// Skip config files (but maybe we want to keep them for reproducibility? User said artifacts generated by agents)
			// Let's keep everything except the ignored dirs.
		}

		content, err := os.ReadFile(path)
		if err != nil {
			return err
		}

		if _, err := r.Storage.Upload(ctx, runID, relPath, content); err != nil {
			log.Printf("Failed to upload artifact %s: %v", relPath, err)
		}
		return nil
	})
}

func (r *Runner) evaluateCode(ctx context.Context, wsPath string, scenConfig *config.ScenarioConfig, stdout string) (*models.EvaluationMetrics, *ValidationReport, error) {
	if scenConfig == nil || len(scenConfig.Validation) == 0 {
		return nil, nil, fmt.Errorf("invalid scenario: no validation rules defined")
	}

	report, err := r.Validate(ctx, wsPath, scenConfig.Validation, stdout)
	if err != nil {
		return nil, nil, err
	}

	// Map Report to EvaluationMetrics for DB stats
	eval := &models.EvaluationMetrics{
		TestsPassed: report.TestsPassed,
		TestsFailed: report.TestsFailed,
		LintIssues:  report.LintIssues,
		Tests:       report.DetailedTests,
		Lints:       report.DetailedLints,
	}

	return eval, report, nil
}

func (r *Runner) FromDBRunResult(dr *models.RunResult) Result {

	res := Result{
		RunID:            dr.ID,
		Alternative:      dr.Alternative,
		Scenario:         dr.Scenario,
		Repetition:       dr.Repetition,
		Duration:         time.Duration(dr.Duration),
		Stdout:           dr.Stdout,
		Stderr:           dr.Stderr,
		ErrorStr:         dr.Error,
		IsSuccess:        dr.IsSuccess,
		ValidationReport: dr.ValidationReport,
		Status:           dr.Status,
		Reason:           dr.Reason,
	}
	if dr.Error != "" {
		res.Error = fmt.Errorf("%s", dr.Error)
	}
	// Evaluation Metrics
	res.EvaluationMetrics = &models.EvaluationMetrics{
		TestsPassed: dr.TestsPassed,
		TestsFailed: dr.TestsFailed,
		LintIssues:  dr.LintIssues,
	}
	// Agent Metrics
	res.AgentMetrics = &parser.AgentMetrics{
		TotalTokens:         dr.TotalTokens,
		InputTokens:         dr.InputTokens,
		OutputTokens:        dr.OutputTokens,
		CachedTokens:        dr.CachedTokens,
		FailedToolCalls:     dr.FailedToolCalls,
		TotalToolCallsCount: dr.ToolCallsCount,
		LoopDetected:        dr.LoopDetected,
	}
	return res
}

func (r *Runner) pollDatabaseForCompletion(ctx context.Context, totalJobs int, resultsChan chan<- Result) {
	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()

	completedIDs := make(map[int64]bool)

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			// Query DB for completed runs in this experiment
			runs, err := r.db.GetCompletedRuns(r.experimentID)
			if err != nil {
				log.Printf("Warning: failed to poll completed runs: %v", err)
				continue
			}

			for _, run := range runs {
				if !completedIDs[run.ID] {
					completedIDs[run.ID] = true
					// Check if this run actually belongs to us? Filtering by experimentID should differ enough.
					// Convert model struct to Result struct
					res := r.FromDBRunResult(&run)
					resultsChan <- res
				}
			}

			if len(completedIDs) >= totalJobs {
				return
			}

			// Also check if experiment was aborted elsewhere?
			exp, err := r.db.GetExperimentByID(r.experimentID)
			if err == nil && (exp.Status == db.ExperimentStatusAborted || exp.Status == db.ExperimentStatusCompleted) && len(completedIDs) < totalJobs {
				// Aborted or marked completed externally
				return
			}
		}
	}
}

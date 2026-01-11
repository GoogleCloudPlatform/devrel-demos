package runner

import (
	"context"
	"encoding/json"
	"fmt"
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

// Runner handles the execution of experiments.
type Runner struct {
	WorkspaceMgr  *workspace.Manager
	MaxConcurrent int
	db            *db.DB
	experimentID  int64
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
	}
}

func (r *Runner) SetDB(d *db.DB) {
	r.db = d
}

func (r *Runner) SetExperimentID(id int64) {
	r.experimentID = id
}

// Checkpoint represents the current progress of an experiment.
type Checkpoint struct {
	TotalJobs     int     `json:"total_jobs"`
	CompletedJobs int     `json:"completed_jobs"`
	Percentage    float64 `json:"percentage"`
	LastUpdate    string  `json:"last_update"`
	Status        string  `json:"status"`
}

// Run executes the experiments defined in the configuration.
func (r *Runner) Run(ctx context.Context, cfg *config.Configuration, timestamp time.Time, experimentDir string) ([]Result, error) {
	var results []Result
	resultsLimit := cfg.Repetitions * len(cfg.Alternatives) * len(cfg.Scenarios)
	resultsChan := make(chan Result, resultsLimit)

	var allAlts []string
	for _, a := range cfg.Alternatives {
		allAlts = append(allAlts, a.Name)
	}

	// 0. Initial checkpoint
	if r.db == nil || r.experimentID == 0 {
		return nil, fmt.Errorf("runner requires valid DB and experiment ID")
	}

	// Ensure logs directory exists
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

	for _, alt := range cfg.Alternatives {
		r.dispatchAlternative(rc, alt, cfg.Scenarios, cfg.Repetitions)
	}

	go func() {
		wg.Wait()
		close(resultsChan)
	}()

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
			// Spec: Status must be COMPLETED for finished runs.
			// Reasons: SUCCESS, VALIDATION, LOOP, ERROR, TIMEOUT.
			res.Status = db.RunStatusCompleted

			switch {
			case res.IsSuccess:
				res.Reason = db.ReasonSuccess
			case res.AgentMetrics != nil && res.AgentMetrics.LoopDetected:
				res.Reason = db.ReasonFailedLoop
			case res.ErrorStr != "" && IsTimeoutErr(res.Error):
				res.Reason = db.ReasonFailedTimeout
			case res.ValidationReport != "":
				res.Reason = db.ReasonFailedValidation
			default:
				res.Reason = db.ReasonFailedError
			}

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
			if res.AgentMetrics != nil {
				runRes.TotalTokens = res.AgentMetrics.TotalTokens
				runRes.InputTokens = res.AgentMetrics.InputTokens
				runRes.OutputTokens = res.AgentMetrics.OutputTokens
				runRes.ToolCallsCount = len(res.AgentMetrics.ToolCalls)
				runRes.FailedToolCalls = res.AgentMetrics.FailedToolCalls
				runRes.LoopDetected = res.AgentMetrics.LoopDetected
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
	if r.checkAction() == "stop" {
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

	var resultFound bool
	var resultFoundMu sync.Mutex

	var terminationRequested bool

	var streamWg sync.WaitGroup
	streamWg.Add(2)

	// Context for raw log batching
	syncCtx, syncCancel := context.WithCancel(jobCtx)
	defer syncCancel()

	// RAW LOG SYNC (Batched every 1s)
	var stdoutMu, stderrMu sync.Mutex
	var currentStdout, currentStderr strings.Builder

	if res.RunID != 0 {
		go r.syncLogs(syncCtx, &res, &stdoutMu, &currentStdout, &stderrMu, &currentStderr)
	}
	// STDOUT STREAMER
	go r.streamStdout(stdoutPipe, logFile, jobID, &res, cmd, &streamWg, &stdoutMu, &currentStdout, &terminationRequested, &resultFound, &resultFoundMu, execCancel)

	// STDERR STREAMER
	go r.streamStderr(stderrPipe, stderrFile, &res, &streamWg, &stderrMu, &currentStderr)

	if err := cmd.Start(); err != nil {
		res.Error = fmt.Errorf("execution failed to start: %w", err)
		res.ErrorStr = res.Error.Error()
		return res
	}

	// Wait for streams and command
	waitErr := r.waitForCommand(cmd, &streamWg, jobCtx, timeout, jobID, &resultFound, &resultFoundMu, &terminationRequested)
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
	// 5. Verify Code (Test & Lint) - skip for timeouts since code is incomplete
	shouldEvaluate := res.Error == nil
	if res.Error != nil && !strings.Contains(res.Error.Error(), "timeout") {
		// Non-timeout errors might still have partial code worth evaluating
		shouldEvaluate = true
	}

	if shouldEvaluate {
		// Use the configuration passed from Manager (in-memory)
		scenConfig := wsInfo.Config

		// Read the metrics log to get stdout content for validation
		// Read logPath content
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
				res.IsSuccess = valReport.OverallSuccess
				jsonBytes, _ := json.Marshal(valReport)
				res.ValidationReport = string(jsonBytes)

				// Aggregate counts into metrics so they show up in DB columns
				if res.EvaluationMetrics == nil {
					res.EvaluationMetrics = &models.EvaluationMetrics{}
				}
				res.EvaluationMetrics.TestsPassed = valReport.TestsPassed
				res.EvaluationMetrics.TestsFailed = valReport.TestsFailed
				res.EvaluationMetrics.LintIssues = valReport.LintIssues
			}
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
		FailedToolCalls:     dr.FailedToolCalls,
		TotalToolCallsCount: dr.ToolCallsCount,
	}
	return res
}

package runner

import (
	"context"
	"fmt"
	"io"
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
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/execution"
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
	executor      execution.Executor
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

	var exec execution.Executor
	if os.Getenv("TENKAI_MODE") == "cloud" {
		log.Println("Initializing CloudRunExecutor...")
		cre, err := execution.NewCloudRunExecutor(context.Background())
		if err != nil {
			log.Fatalf("Failed to initialize CloudRunExecutor: %v", err)
		}
		exec = cre
	} else {
		log.Println("Initializing LocalExecutor...")
		exec = execution.NewLocalExecutor()
	}

	return &Runner{
		WorkspaceMgr:  wsMgr,
		MaxConcurrent: maxConcurrent,
		executor:      exec,
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

	log.Printf("Starting experiment with %d unique jobs. Max concurrency: %d", resultsLimit, r.MaxConcurrent)

	for i := 1; i <= cfg.Repetitions; i++ {
		for _, scenPath := range cfg.Scenarios {
			for _, alt := range cfg.Alternatives {
				r.dispatchRun(rc, alt, scenPath, i)
			}
		}
	}

	go func() {
		wg.Wait()
		close(resultsChan)
	}()

	completed := 0
	stopping := false
	lastLogTime := time.Now()
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
			// Reset heartbeat timer on activity
			lastLogTime = time.Now()

			// Refine Reason and Status before appending to results slice
			// Spec: Status must be COMPLETED for finished runs.
			// Reasons: SUCCESS, VALIDATION, LOOP, ERROR, TIMEOUT.
			// If we are stopping, and this result was cancelled/aborted, verify status.

			// ... (rest of processing logic remains)

			if stopping && !res.IsSuccess {
				res.Status = db.RunStatusAborted
				res.Reason = "CANCELLED"
			} else {
				res.Status = db.RunStatusCompleted
			}

			switch {
			case res.IsSuccess:
				res.Status = db.RunStatusCompleted // Ensure success is always completed
				res.Reason = db.ReasonSuccess
			case res.Status == db.RunStatusAborted:
				// Already handled above
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
			// 4. Fetch authoritative metrics from DB (Single Source of Truth)
			var dbMetrics *parser.AgentMetrics
			var fetchErr error

			// Retry fetching metrics to handle transient DB issues or read-after-write delays
			for attempt := 0; attempt < 5; attempt++ {
				dbMetrics, fetchErr = r.db.GetRunMetrics(res.RunID)
				if fetchErr == nil {
					break
				}
				time.Sleep(100 * time.Millisecond * time.Duration(1<<attempt))
			}

			if fetchErr != nil {
				return results, fmt.Errorf("failed to fetch authoritative metrics for run %d after retries: %w", res.RunID, fetchErr)
			}

			// Update the Result object so that CalculateSummary (which uses res.AgentMetrics) is correct
			res.AgentMetrics = dbMetrics

			// Sync to runRes for DB persistence in run_results table
			runRes.TotalTokens = dbMetrics.TotalTokens
			runRes.InputTokens = dbMetrics.InputTokens
			runRes.OutputTokens = dbMetrics.OutputTokens
			runRes.ToolCallsCount = dbMetrics.TotalToolCallsCount
			runRes.FailedToolCalls = dbMetrics.FailedToolCalls
			runRes.LoopDetected = dbMetrics.LoopDetected

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
			// Heartbeat Log
			if time.Since(lastLogTime) > 30*time.Second {
				percentage := float64(completed) / float64(resultsLimit) * 100
				log.Printf("Heartbeat: Still working. Progress: %d/%d (%.1f%%)", completed, resultsLimit, percentage)
				lastLogTime = time.Now()
			}

			if stopping {
				continue
			}

			// Periodically check for STOP signal from DB to cancel context
			action := r.checkAction()
			if action == "stop" {
				log.Printf("[Runner] Received STOP signal for Experiment %d. Canceling context...", r.experimentID)
				cancel()
				stopping = true
				// Do NOT drain channel. Let the loop continue to process results as they finish/error out.
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
	log.Printf("STARTED %s", jobID)

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
	// 2. Prepare I/O Pipes
	// We use io.Pipe to connect the Executor's output (Writer) to the Runner's streaming logic (Reader).
	stdoutReader, stdoutWriter := io.Pipe()
	stderrReader, stderrWriter := io.Pipe()
	stdinReader, stdinWriter := io.Pipe()

	// 3. Prepare Command Config
	cmdCfg, jobCtx, jobCancel, _, execCancel, err := r.createJobConfig(ctx, alt, wsInfo, timeout, jobID)
	if err != nil {
		res.Error = fmt.Errorf("job config creation failed: %w", err)
		res.ErrorStr = res.Error.Error()
		return res
	}
	defer jobCancel()
	defer execCancel()

	// 4. Setup Log Files
	logFile, stderrFile, logPath, err := r.setupLogFiles(wsInfo, alt.Name, scenarioID, rep)
	if err != nil {
		res.Error = err
		res.ErrorStr = res.Error.Error()
		return res
	}
	defer logFile.Close()
	defer stderrFile.Close()

	// 5. Start Streaming - PROMPT.md to Stdin
	promptPath := filepath.Join(wsInfo.Project, "PROMPT.md")
	go func() {
		// Close writer after streaming to signal EOF to executor
		defer stdinWriter.Close()
		r.streamPromptContents(promptPath, stdinWriter)
	}()

	var resultFound bool
	var resultFoundMu sync.Mutex
	var terminationRequested bool
	var streamWg sync.WaitGroup
	streamWg.Add(2)

	// Context for raw log batching
	syncCtx, syncCancel := context.WithCancel(jobCtx)
	defer syncCancel()

	var stdoutMu, stderrMu sync.Mutex
	var currentStdout, currentStderr strings.Builder

	if res.RunID != 0 {
		go r.syncLogs(syncCtx, &res, &stdoutMu, &currentStdout, &stderrMu, &currentStderr)
	}

	// STDOUT STREAMER
	// We pass 'stdoutReader' instead of cmd.StdoutPipe
	go r.streamStdout(stdoutReader, logFile, jobID, &res, nil, &streamWg, &stdoutMu, &currentStdout, &terminationRequested, &resultFound, &resultFoundMu, execCancel)

	// STDERR STREAMER
	go r.streamStderr(stderrReader, stderrFile, &res, &streamWg, &stderrMu, &currentStderr)

	// 6. Execute Job (Access Executor via blocking call in goroutine? No, Execute is blocking)
	// We run Execute in a goroutine so we can wait for streams?
	// Actually, Execute blocks until completion. The streams are being read in other goroutines.
	// But we need to close the write-end of the pipes when Execute finishes so readers get EOF.

	execResChan := make(chan execution.ExecutionResult, 1)

	go func() {
		defer stdoutWriter.Close()
		defer stderrWriter.Close()
		execRes := r.executor.Execute(jobCtx, cmdCfg, stdinReader, stdoutWriter, stderrWriter)
		execResChan <- execRes
	}()

	// Wait for streams (which wait for pipe verify/EOF)
	// Note: waitForCommand logic needs adjustment. It relied on cmd.Wait().
	// Now we wait for the result from channel AND streams.

	// Wait for execution to finish
	execRes := <-execResChan

	// Wait for streams to drain
	streamWg.Wait()

	if execRes.Error != nil {
		res.Error = execRes.Error
		res.ErrorStr = res.Error.Error()
	} else if execRes.ExitCode != 0 {
		res.Error = fmt.Errorf("exit code %d", execRes.ExitCode)
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

	// Finalize IsSuccess using centralized logic
	if res.Error != nil {
		res.IsSuccess = false
	}
	// res.IsSuccess is already set by Validation/EarlyExit logic

	// Ensure live monitor is stopped before returning to avoid race conditions on DB
	jobCancel()

	statusStr := "Success"
	if !res.IsSuccess {
		statusStr = "Failed"
		if res.ErrorStr != "" {
			statusStr = fmt.Sprintf("Failed (%s)", res.ErrorStr)
		}
	}
	log.Printf("COMPLETED %s [%s] in %s", jobID, statusStr, res.Duration.Round(time.Millisecond))

	// Result will be saved to DB in the main Run loop
	return res
}

func (r *Runner) evaluateCode(ctx context.Context, wsPath string, scenConfig *config.ScenarioConfig, stdout string) (*models.EvaluationMetrics, *ValidationReport, error) {
	if scenConfig == nil || len(scenConfig.Validation) == 0 {
		return nil, nil, fmt.Errorf("invalid scenario: no validation rules defined")
	}

	report, err := r.Validate(ctx, wsPath, scenConfig.Validation, stdout, scenConfig.Env)
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

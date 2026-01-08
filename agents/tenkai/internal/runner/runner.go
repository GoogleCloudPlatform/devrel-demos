package runner

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/parser"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/workspace"
)

// EvaluationMetrics is now in db.EvaluationMetrics

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

	AgentMetrics      *parser.AgentMetrics  `json:"agent_metrics,omitempty"`
	EvaluationMetrics *db.EvaluationMetrics `json:"evaluation_metrics,omitempty"`
	GeneratedFiles    []db.RunFile          `json:"generated_files,omitempty"`
	IsSuccess         bool                  `json:"is_success"`
	ValidationReport  string                `json:"validation_report"`
	Status            string                `json:"status"` // QUEUED, RUNNING, COMPLETED, ABORTED
	Reason            string                `json:"reason"` // SUCCESS, FAILURE, TIMEOUT, LOOP, ERROR
}

// IsSuccess returns true if the run result is considered a success.
func (r Result) Success() bool {
	if r.ValidationReport != "" {
		return r.IsSuccess
	}
	if r.Error != nil {
		return false
	}
	// For legacy runs, we expect at least one test to pass
	if r.EvaluationMetrics != nil {
		return r.EvaluationMetrics.TestsPassed > 0
	}
	// If no evaluation data at all, it can't be a legacy success
	return false
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
	completedCount := 0

	var allAlts []string
	for _, a := range cfg.Alternatives {
		allAlts = append(allAlts, a.Name)
	}

	// 0. Initial checkpoint
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

	var terminalResults []Result
	if r.db != nil && r.experimentID != 0 {
		dbResults, err := r.db.GetRunResults(r.experimentID)
		if err == nil {
			for _, dr := range dbResults {
				res := r.FromDBRunResult(dr)
				status := strings.ToUpper(res.Status)

				// Only consider SUCCESS or FAILED as "completed" for the purposes of skipping
				if status != db.RunStatusRunning && status != db.RunStatusQueued && status != "" {
					terminalResults = append(terminalResults, res)
					completedCount++
				}
			}
			log.Printf("Synchronized with DB: found %d terminal results (total found: %d) for Experiment %d", completedCount, len(dbResults), r.experimentID)

			// 1. Initial summary update (using ALL results for initial picture, but we'll re-run non-terminals)
			// Actually, just use terminalResults for the baseline summary
			results = append(results, terminalResults...)

			var allAlts []string
			for _, a := range cfg.Alternatives {
				allAlts = append(allAlts, a.Name)
			}
			summary := CalculateSummary(results, cfg.Control, allAlts)
			r.UpdateDBFromResults(summary)

			// 2. Update initial progress
			r.db.UpdateExperimentProgress(r.experimentID, completedCount, resultsLimit)
		}
	}

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

	for _, alt := range cfg.Alternatives {
		for _, scenPath := range cfg.Scenarios {
			// Determine scenario identifier from path basename
			scenID := filepath.Base(scenPath)

			for i := 1; i <= cfg.Repetitions; i++ {
				// Skip if already in results (loaded from DB)
				alreadyDone := false
				for _, r := range results {
					if r.Alternative == alt.Name && r.Scenario == scenID && r.Repetition == i {
						alreadyDone = true
						break
					}
				}
				if alreadyDone {
					continue
				}

				// Insert "Running" status
				var runID int64
				if r.db != nil && r.experimentID != 0 {
					prerun := &db.RunResult{
						ExperimentID: r.experimentID,
						Alternative:  alt.Name,
						Scenario:     scenID,
						Repetition:   i,
						Status:       db.RunStatusQueued,
					}
					if id, err := r.db.SaveRunResult(prerun); err == nil {
						runID = id
					} else {
						log.Printf("Warning: failed to save initial run state: %v", err)
					}
				}

				wg.Add(1)
				go func(alt config.Alternative, sID string, path string, rep int, dbRunID int64) {
					defer wg.Done()

					// Check for stop/pause BEFORE acquiring semaphore
					for {
						action := r.checkAction(experimentDir)
						if action == "stop" {
							return
						}
						if action == "pause" {
							time.Sleep(1 * time.Second)
							continue
						}
						break
					}

					select {
					case sem <- struct{}{}:
						defer func() { <-sem }()
					case <-ctx.Done():
						return
					}
					// Mark as RUNNING just before execution
					if r.db != nil && dbRunID != 0 {
						r.db.UpdateRunStatus(dbRunID, db.RunStatusRunning)
					}

					res := r.runSingle(ctx, timestamp, cfg.Name, alt, sID, path, rep, experimentDir, timeout, dbRunID)
					resultsChan <- res
				}(alt, scenID, scenPath, i, runID)
			}
		}
	}

	go func() {
		wg.Wait()
		close(resultsChan)
	}()

	completed := completedCount
	for {
		select {
		case res, ok := <-resultsChan:
			if !ok {
				// All current jobs finished or stopped.
				// Final status update for the experiment
				if r.db != nil && r.experimentID != 0 {
					finalStatus := db.ExperimentStatusCompleted
					if len(results) < resultsLimit {
						finalStatus = db.ExperimentStatusAborted
					}
					r.db.UpdateExperimentStatus(r.experimentID, finalStatus)
				}
				goto Done
			}
			completed++

			// Refine Reason and Status before appending to results slice
			// Spec: Status must be COMPLETED for finished runs.
			// Reasons: SUCCESS, VALIDATION, LOOP, ERROR, TIMEOUT.
			res.Status = db.RunStatusCompleted

			if res.IsSuccess {
				res.Reason = db.ReasonSuccess
			} else {
				if res.AgentMetrics != nil && res.AgentMetrics.LoopDetected {
					res.Reason = db.ReasonFailedLoop
				} else if res.ErrorStr != "" && IsTimeoutErr(res.Error) {
					res.Reason = db.ReasonFailedTimeout
				} else if res.EvaluationMetrics != nil && res.EvaluationMetrics.TestsFailed > 0 {
					res.Reason = db.ReasonFailedValidation
				} else if res.ErrorStr != "" {
					res.Reason = db.ReasonFailedError
					// Fallback for failures without explicit error/loop/timeout
					res.Reason = db.ReasonFailedValidation
				}
			}

			percentage := float64(completed) / float64(resultsLimit) * 100
			log.Printf("Progress: %d/%d jobs completed (%.1f%%)", completed, resultsLimit, percentage)

			savedToDB := false
			if r.db != nil && r.experimentID != 0 && res.RunID != 0 {
				runRes := &db.RunResult{
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
					runRes.LoopDetected = res.AgentMetrics.LoopDetected
				}

				// Build Telemetry for Final Save
				telemetry := &db.RunTelemetry{
					Result: runRes,
				}

				if res.AgentMetrics != nil {

					for _, tc := range res.AgentMetrics.ToolCalls {
						telemetry.ToolUsage = append(telemetry.ToolUsage, db.ToolUsage{
							RunID:     res.RunID,
							Name:      tc.Name,
							Args:      tc.Args,
							Status:    tc.Status,
							Output:    tc.Output,
							Error:     tc.Error,
							Duration:  tc.Duration.Nanoseconds(),
							Timestamp: tc.Timestamp,
						})
					}
					// Messages
					for _, m := range res.AgentMetrics.Messages {
						telemetry.Messages = append(telemetry.Messages, db.Message{
							RunID:     res.RunID,
							Role:      m.Role,
							Content:   m.Content,
							Timestamp: m.Timestamp,
						})
					}
					// Evaluation Details
					if res.EvaluationMetrics != nil {
						telemetry.TestResults = res.EvaluationMetrics.Tests
						telemetry.LintResults = res.EvaluationMetrics.Lints
					}
				}
				// Transactional Save
				if err := r.db.SaveRunTelemetry(telemetry); err != nil {
					log.Printf("Warning: failed to save final run telemetry: %v", err)
				} else {
					savedToDB = true
				}
			}

			// Only append to results and update summary if the record was successfully saved to DB
			// or if we are not using a DB. This ensures the summary and investigation tab match.
			if savedToDB || r.db == nil {
				results = append(results, res)

				// Re-calculate and update summaries intermittently
				// Update on every run completion to ensure UI is responsive
				summary := CalculateSummary(results, cfg.Control, allAlts)
				r.UpdateDBFromResults(summary)
			}

		case <-time.After(1 * time.Second):

			// Periodically check for STOP signal from DB to cancel context
			action := r.checkAction(experimentDir)
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
	if r.checkAction(experimentDir) == "stop" {
		finalStatus = db.ExperimentStatusAborted // Use consistent status
	}
	if r.db != nil && r.experimentID != 0 {

		r.db.UpdateExperimentStatus(r.experimentID, finalStatus)

		// Calculate final summary

		summary := CalculateSummary(results, cfg.Control, allAlts)
		r.UpdateDBFromResults(summary)
	}

	return results, nil
}

func (r *Runner) UpdateDBFromResults(summary *ExperimentSummary) {
	if r.db == nil || r.experimentID == 0 {
		return
	}
	// Append-only: Do not delete old summaries. Just insert new snapshot.
	for _, s := range summary.Alternatives {
		s.ExperimentID = r.experimentID
		if err := r.db.SaveExperimentSummary(&s); err != nil {
			log.Printf("Warning: failed to save summary for %s: %v", s.Alternative, err)
		}
	}

	// NEW: Update global experiment metrics in the experiments table
	if err := r.db.UpdateExperimentMetrics(
		r.experimentID,
		summary.SuccessRate,
		summary.AvgDuration,
		summary.AvgTokens,
		summary.TotalLint,
		summary.SuccessfulRuns,
	); err != nil {
		log.Printf("Warning: failed to update global experiment metrics: %v", err)
	}
}

func (r *Runner) checkAction(experimentDir string) string {
	if r.db == nil || r.experimentID == 0 {
		return ""
	}
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

func (r *Runner) runSingle(ctx context.Context, timestamp time.Time, experimentName string, alt config.Alternative, scenarioID string, scenarioPath string, rep int, experimentDir string, timeout time.Duration, runID int64) Result {
	start := time.Now()

	res := Result{
		RunID:       runID,
		Alternative: alt.Name,
		Scenario:    scenarioID,
		Repetition:  rep,
	}

	// Calculate a simple ID or just use Name/Scen/Rep for logging
	jobID := fmt.Sprintf("[%s|%s|#%d]", alt.Name, scenarioID, rep)
	log.Printf("START %s", jobID)

	// Ensure paths are absolute before passing to WorkspaceMgr
	opts := workspace.WorkspaceOptions{
		SettingsPath:     alt.SettingsPath,
		Settings:         alt.Settings,
		ContextPath:      alt.ContextFilePath,
		Context:          alt.Context,
		SystemPromptPath: alt.SystemPromptFile,
		SystemPrompt:     alt.SystemPrompt,
		PolicyFiles:      alt.PolicyFiles,
	}

	if opts.SettingsPath != "" {
		if abs, err := filepath.Abs(opts.SettingsPath); err == nil {
			opts.SettingsPath = abs
		}
	}
	if opts.ContextPath != "" {
		if abs, err := filepath.Abs(opts.ContextPath); err == nil {
			opts.ContextPath = abs
		}
	}
	if opts.SystemPromptPath != "" {
		if abs, err := filepath.Abs(opts.SystemPromptPath); err == nil {
			opts.SystemPromptPath = abs
		}
	}
	wsInfo, err := r.WorkspaceMgr.PrepareWorkspace(experimentDir, alt.Name, scenarioID, rep, opts)
	if err != nil {
		res.Error = fmt.Errorf("workspace prep failed: %w", err)
		res.ErrorStr = res.Error.Error()
		return res
	}
	res.Workspace = wsInfo.Project

	// Anchor the workspace to prevent Gemini from walking up to tenkai root
	// REMOVED: Do not auto-create go.mod. It interferes with scenarios where the agent must init the module.
	// If isolation is needed, we should rely on the agent creating it or the scenario template providing it.
	// 1. Prepare Command with timeout
	cmdName := alt.Command
	cmdArgs := make([]string, len(alt.Args))
	copy(cmdArgs, alt.Args)

	// Handle System Prompt File (SYSTEM.md in workspace project dir)

	// Check if configured, resolve absolute path if needed
	envMap := make(map[string]string)
	for k, v := range alt.Env {
		envMap[k] = v
	}

	systemPath := filepath.Join(wsInfo.Project, "SYSTEM.md")
	if _, err := os.Stat(systemPath); err == nil {
		envMap["GEMINI_SYSTEM_MD"] = systemPath
	}

	// 2. Pass PROMPT.md content as the last argument
	// This ensures the CLI runs in non-interactive mode (batch) rather than REPL mode.
	promptPath := filepath.Join(wsInfo.Project, "PROMPT.md")
	promptContent, err := os.ReadFile(promptPath)
	if err == nil {
		cmdArgs = append(cmdArgs, string(promptContent))
	} else {
		// If PROMPT.md is missing, this runs without prompt!
		// But it should be there from template copy.
		res.Error = fmt.Errorf("PROMPT.md missing: %w", err)
		res.ErrorStr = res.Error.Error()
		return res
	}

	// Create timeout context for the entire job (run + verification)
	jobCtx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	cmd := exec.CommandContext(jobCtx, cmdName, cmdArgs...)
	cmd.Dir = wsInfo.Project

	// Create a new Process Group to handle orphan cleanup
	cmd.SysProcAttr = &syscall.SysProcAttr{Setpgid: true}

	// Ensure that on context cancellation (timeout or abort), we kill the whole process group
	cmd.Cancel = func() error {
		if cmd.Process != nil {
			log.Printf("[Runner] Kill signal triggered for %s (PID %d)", jobID, cmd.Process.Pid)
			// Kill the process group by passing negative PID (works because Setpgid: true)
			return syscall.Kill(-cmd.Process.Pid, syscall.SIGKILL)
		}
		return nil
	}

	// Ensure that if the process exits but leaves children keeping pipes open, we don't hang forever
	cmd.WaitDelay = 2 * time.Second

	cmd.Env = os.Environ()
	// Override HOME to force config isolation (CLI looks in ~/.gemini)
	// Traps Go mod cache in wsInfo.Home
	cmd.Env = append(cmd.Env, fmt.Sprintf("HOME=%s", wsInfo.Home))

	for k, v := range envMap {
		cmd.Env = append(cmd.Env, fmt.Sprintf("%s=%s", k, v))
	}
	// 3. Capture Output (Real-time Stream)
	safeAlt := strings.ReplaceAll(alt.Name, " ", "_")
	safeScen := strings.ReplaceAll(scenarioID, " ", "_")
	logFilename := fmt.Sprintf("%s_%s_rep%d", safeAlt, safeScen, rep)

	logPath := filepath.Join(wsInfo.Logs, logFilename+".jsonl")
	logFile, err := os.Create(logPath)
	if err != nil {
		res.Error = fmt.Errorf("failed to create events log: %w", err)
		res.ErrorStr = res.Error.Error()
		return res
	}
	defer logFile.Close()

	stderrPath := filepath.Join(wsInfo.Logs, logFilename+".stderr.log")
	stderrFile, err := os.Create(stderrPath)
	if err != nil {
		res.Error = fmt.Errorf("failed to create stderr log: %w", err)
		res.ErrorStr = res.Error.Error()
		return res
	}
	defer stderrFile.Close()

	stdoutPipe, _ := cmd.StdoutPipe()
	stderrPipe, _ := cmd.StderrPipe()

	// CRITICAL: Ensure clean EOF for Stdin to prevent hangs
	cmd.Stdin = strings.NewReader("")

	var streamWg sync.WaitGroup
	streamWg.Add(2)

	// Context for raw log batching
	syncCtx, syncCancel := context.WithCancel(jobCtx)
	defer syncCancel()

	// RAW LOG SYNC (Batched every 1s)
	var stdoutMu, stderrMu sync.Mutex
	var currentStdout, currentStderr strings.Builder

	if r.db != nil && res.RunID != 0 {
		go func() {
			ticker := time.NewTicker(1 * time.Second)
			defer ticker.Stop()
			for {
				select {
				case <-syncCtx.Done():
					return
				case <-ticker.C:
					stdoutMu.Lock()
					out := currentStdout.String()
					stdoutMu.Unlock()
					stderrMu.Lock()
					errStr := currentStderr.String()
					stderrMu.Unlock()
					r.db.UpdateRunLogs(res.RunID, out, errStr)
				}
			}
		}()
	}

	// STDOUT STREAMER
	go func() {
		defer streamWg.Done()
		scanner := bufio.NewScanner(stdoutPipe)
		metrics := &parser.AgentMetrics{}
		pendingTools := make(map[string]*parser.ToolCall)
		var lastToolCount, lastMsgCount int

		for scanner.Scan() {
			line := scanner.Text()
			fmt.Fprintln(logFile, line)

			stdoutMu.Lock()
			currentStdout.WriteString(line + "\n")
			stdoutMu.Unlock()

			// Real-time parsing and event emission
			if err := parser.ParseLine(line, metrics, pendingTools); err == nil {
				if r.db != nil && res.RunID != 0 {
					// Check for new tool results or messages
					if len(metrics.ToolCalls) > lastToolCount {
						newTools := metrics.ToolCalls[lastToolCount:]
						for _, tc := range newTools {
							r.db.SaveRunEvent(res.RunID, "tool", tc)
						}
						lastToolCount = len(metrics.ToolCalls)
					}
					if len(metrics.Messages) > lastMsgCount {
						newMsgs := metrics.Messages[lastMsgCount:]
						for _, msg := range newMsgs {
							r.db.SaveRunEvent(res.RunID, "message", msg)
						}
						lastMsgCount = len(metrics.Messages)
					}
				}
			}
		}
	}()

	// STDERR STREAMER
	go func() {
		defer streamWg.Done()
		scanner := bufio.NewScanner(stderrPipe)
		for scanner.Scan() {
			line := scanner.Text()
			fmt.Fprintln(stderrFile, line)
			stderrMu.Lock()
			currentStderr.WriteString(line + "\n")
			stderrMu.Unlock()
		}
	}()

	if err := cmd.Start(); err != nil {
		res.Error = fmt.Errorf("execution failed to start: %w", err)
		res.ErrorStr = res.Error.Error()
		return res
	}

	// Wait for streams to finish (pipes closed)
	streamWg.Wait()

	if err := cmd.Wait(); err != nil {
		// Check if timeout
		if jobCtx.Err() == context.DeadlineExceeded {
			res.Error = fmt.Errorf("execution timeout (%v limit)", timeout)
		} else {
			res.Error = fmt.Errorf("execution failed: %w", err)
		}
		res.ErrorStr = res.Error.Error()
	}

	res.Duration = time.Since(start)

	// Final raw log sync
	if r.db != nil && res.RunID != 0 {
		r.db.UpdateRunLogs(res.RunID, currentStdout.String(), currentStderr.String())
	}

	res.Stdout = currentStdout.String()
	res.Stderr = currentStderr.String()

	// 4. Load Metrics from DB (Single Source of Truth)

	// We rely on the live monitor having populated the run_events table.
	if r.db != nil && res.RunID != 0 {
		metrics, err := r.db.GetRunMetrics(res.RunID)
		if err == nil {
			res.AgentMetrics = metrics
		} else {
			log.Printf("Warning: failed to load metrics from DB for run %d: %v", res.RunID, err)
		}
	} else {
		// Fallback for non-DB runs (e.g. testing)
		metrics, err := parser.ParseEvents(logPath)
		if err == nil {
			res.AgentMetrics = metrics
		} else {
			log.Printf("Warning: failed to parse metrics from %s: %v", logPath, err)
		}
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

				// NEW: Aggregate counts into metrics so they show up in DB columns
				if res.EvaluationMetrics == nil {
					res.EvaluationMetrics = &db.EvaluationMetrics{}
				}
				res.EvaluationMetrics.TestsPassed = valReport.TestsPassed
				res.EvaluationMetrics.TestsFailed = valReport.TestsFailed
				res.EvaluationMetrics.LintIssues = valReport.LintIssues
			}
		}
	}

	// Finalize IsSuccess using centralized logic
	res.IsSuccess = res.Success()

	// 6. Snapshot Workspace Files (Project dir only)
	res.GeneratedFiles = r.captureFiles(wsInfo.Project)

	// Ensure live monitor is stopped before returning to avoid race conditions on DB
	cancel()

	log.Printf("DONE  %s in %s", jobID, res.Duration.Round(time.Millisecond))
	// Result will be saved to DB in the main Run loop
	return res
}

func (r *Runner) captureFiles(wsPath string) []db.RunFile {
	var files []db.RunFile
	err := filepath.Walk(wsPath, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if info.IsDir() {
			return nil
		}

		// Skip hidden files/dirs like .gemini, .git
		rel, _ := filepath.Rel(wsPath, path)
		parts := strings.Split(rel, string(filepath.Separator))
		for _, p := range parts {
			if strings.HasPrefix(p, ".") {
				return nil
			}
		}

		// Skip PROMPT.md (it's internal)
		if rel == "PROMPT.md" {
			return nil
		}

		content, err := os.ReadFile(path)
		if err != nil {
			log.Printf("Warning: failed to read file %s for snapshot: %v", path, err)
			return nil
		}

		files = append(files, db.RunFile{
			Path:        rel,
			Content:     string(content),
			IsGenerated: true, // For now assuming everything not skipped is generated or relevant
		})
		return nil
	})

	if err != nil {
		log.Printf("Warning: failed to walk workspace for snapshot: %v", err)
	}
	return files
}
func (r *Runner) evaluateCode(ctx context.Context, wsPath string, scenConfig *config.ScenarioConfig, stdout string) (*db.EvaluationMetrics, *ValidationReport, error) {
	if scenConfig == nil || len(scenConfig.Validation) == 0 {
		return nil, nil, fmt.Errorf("invalid scenario: no validation rules defined")
	}

	report, err := r.Validate(ctx, wsPath, scenConfig.Validation, stdout)
	if err != nil {
		return nil, nil, err
	}

	// Map Report to EvaluationMetrics for DB stats
	eval := &db.EvaluationMetrics{
		TestsPassed: report.TestsPassed,
		TestsFailed: report.TestsFailed,
		LintIssues:  report.LintIssues,
	}
	// Note: We don't have individual TestResults mapped back to eval.Tests in new engine yet,
	// but the ValidationReport JSON contains all details.
	// If backward compatibility for eval.Tests slice is needed, we'd map it here.
	// For now, rely on ValidationReport.
	return eval, report, nil
}

func (r *Runner) FromDBRunResult(dr *db.RunResult) Result {

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
	res.EvaluationMetrics = &db.EvaluationMetrics{
		TestsPassed: dr.TestsPassed,
		TestsFailed: dr.TestsFailed,
		LintIssues:  dr.LintIssues,
	}
	// Agent Metrics
	res.AgentMetrics = &parser.AgentMetrics{
		TotalTokens:  dr.TotalTokens,
		InputTokens:  dr.InputTokens,
		OutputTokens: dr.OutputTokens,
	}
	return res
}

func (r *Runner) generateLegacyReport(metrics *db.EvaluationMetrics) *ValidationReport {
	if metrics == nil {
		return nil
	}

	report := &ValidationReport{
		OverallSuccess: metrics.TestsPassed > 0 && metrics.TestsFailed == 0,
		TestsPassed:    metrics.TestsPassed,
		TestsFailed:    metrics.TestsFailed,
		LintIssues:     metrics.LintIssues,
		Items:          []ValidationItem{},
	}

	if len(metrics.Tests) > 0 {
		for _, t := range metrics.Tests {
			report.Items = append(report.Items, ValidationItem{
				Type:        "test",
				Status:      t.Status,
				Description: t.Name,
				Details:     t.Output,
			})
		}
	} else {
		report.Items = append(report.Items, ValidationItem{
			Type:        "test",
			Status:      "FAIL",
			Description: "Legacy Test Run",
			Details:     "No tests found or executed",
		})
	}

	lintStatus := "PASS"
	lintDetails := "No lint issues"
	if metrics.LintIssues > 0 {
		lintStatus = "FAIL"
		lintDetails = fmt.Sprintf("Found %d lint issues", metrics.LintIssues)
	}

	report.Items = append(report.Items, ValidationItem{
		Type:        "lint",
		Status:      lintStatus,
		Description: "Legacy Lint Check",
		Details:     lintDetails,
	})

	return report
}

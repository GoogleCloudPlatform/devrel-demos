package runner

import (
	"bufio"
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/parser"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/workspace"
)

// EvaluationMetrics holds the results of code verification.
type EvaluationMetrics struct {
	TestsPassed int
	TestsFailed int
	LintIssues  int
	Tests       []db.TestResult
	Lints       []db.LintIssue
}

// Result represents the outcome of a single experiment run.
type Result struct {
	Alternative string        `json:"alternative"`
	Scenario    string        `json:"scenario"`
	Repetition  int           `json:"repetition"`
	Duration    time.Duration `json:"duration"`
	Workspace   string        `json:"workspace"`
	Stdout      string        `json:"stdout"`
	Stderr      string        `json:"stderr"`
	Error       error         `json:"-"` // Don't marshal interface
	ErrorStr    string        `json:"error,omitempty"`

	AgentMetrics      *parser.AgentMetrics `json:"agent_metrics,omitempty"`
	EvaluationMetrics *EvaluationMetrics   `json:"evaluation_metrics,omitempty"`
	GeneratedFiles    []db.RunFile         `json:"generated_files,omitempty"`
	IsSuccess         bool                 `json:"is_success"`
	Score             int                  `json:"score"`
	ValidationReport  string               `json:"validation_report"`
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

	// Initial checkpoint
	if r.db != nil && r.experimentID != 0 {
		r.db.UpdateExperimentProgress(r.experimentID, 0, resultsLimit)
		r.db.UpdateExperimentStatus(r.experimentID, "running")
	}

	// Parse timeout from config
	timeout := 5 * time.Minute
	if cfg.Timeout != "" {
		if d, err := time.ParseDuration(cfg.Timeout); err == nil {
			timeout = d
		} else {
			log.Printf("Warning: invalid timeout %q, using default 5m", cfg.Timeout)
		}
	}

	for _, alt := range cfg.Alternatives {
		for _, scen := range cfg.Scenarios {
			for i := 1; i <= cfg.Repetitions; i++ {
				wg.Add(1)
				go func(alt config.Alternative, scen config.Scenario, rep int) {
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

					res := r.runSingle(ctx, timestamp, cfg.Name, alt, scen, rep, experimentDir, timeout)
					resultsChan <- res
				}(alt, scen, i)
			}
		}
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
				goto Done
			}
			completed++
			percentage := float64(completed) / float64(resultsLimit) * 100
			log.Printf("Progress: %d/%d jobs completed (%.1f%%)", completed, resultsLimit, percentage)
			if r.db != nil && r.experimentID != 0 {
				runRes := &db.RunResult{
					ExperimentID: r.experimentID,
					Alternative:  res.Alternative,
					Scenario:     res.Scenario,
					Repetition:   res.Repetition,
					Duration:     int64(res.Duration),
					Error:        res.ErrorStr,
					Stdout:       res.Stdout,
					Stderr:       res.Stderr,
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

				runRes.IsSuccess = res.IsSuccess
				runRes.Score = res.Score
				runRes.ValidationReport = res.ValidationReport

				// 1. Save Run Result (returns ID for FKs)
				runID, err := r.db.SaveRunResult(runRes)
				if err != nil {
					log.Printf("Warning: failed to save run result to DB: %v", err)
				} else if res.AgentMetrics != nil {
					// 2. Save Tool Usage
					for _, tc := range res.AgentMetrics.ToolCalls {
						tu := &db.ToolUsage{
							RunID:     runID,
							Name:      tc.Name,
							Args:      tc.Args,
							Status:    tc.Status,
							Output:    tc.Output,
							Error:     tc.Error,
							Duration:  int64(tc.Duration),
							Timestamp: tc.Timestamp,
						}
						if err := r.db.SaveToolUsage(tu); err != nil {
							log.Printf("Warning: failed to save tool usage: %v", err)
						}
					}
					// 3. Save Messages
					for _, m := range res.AgentMetrics.Messages {
						msg := &db.Message{
							RunID:     runID,
							Role:      m.Role,
							Content:   m.Content,
							Timestamp: m.Timestamp,
						}
						if err := r.db.SaveMessage(msg); err != nil {
							log.Printf("Warning: failed to save message: %v", err)
						}
					}

					// 5. Save Detailed Evaluation
					if res.EvaluationMetrics != nil {
						for i := range res.EvaluationMetrics.Tests {
							res.EvaluationMetrics.Tests[i].RunID = runID
						}
						if err := r.db.SaveTestResults(res.EvaluationMetrics.Tests); err != nil {
							log.Printf("Warning: failed to save test results: %v", err)
						}

						for i := range res.EvaluationMetrics.Lints {
							res.EvaluationMetrics.Lints[i].RunID = runID
						}
						if err := r.db.SaveLintResults(res.EvaluationMetrics.Lints); err != nil {
							log.Printf("Warning: failed to save lint results: %v", err)
						}
					}
				}
				r.db.UpdateExperimentProgress(r.experimentID, completed, resultsLimit)
			}
			results = append(results, res)
		case <-time.After(1 * time.Second):
			// Periodically check for STOP signal from DB to cancel context
			action := r.checkAction(experimentDir)
			if action == "stop" {
				cancel()
				// Drain channel
				for range resultsChan {
				}
				goto Done
			}
			if action == "pause" {
				if r.db != nil && r.experimentID != 0 {
					r.db.UpdateExperimentStatus(r.experimentID, "paused")
				}
			} else if action == "resume" {
				if r.db != nil && r.experimentID != 0 {
					r.db.UpdateExperimentStatus(r.experimentID, "running")
				}
			}
		}
	}

Done:
	// Final checkpoint
	finalStatus := "completed"
	if r.checkAction(experimentDir) == "stop" {
		finalStatus = "stopped"
	}
	if r.db != nil && r.experimentID != 0 {
		r.db.UpdateExperimentProgress(r.experimentID, completed, resultsLimit)
		r.db.UpdateExperimentStatus(r.experimentID, finalStatus)

		// Calculate and persist summaries (3rd NF)
		summary := CalculateSummary(results, cfg.Control)
		r.db.DeleteExperimentSummaries(r.experimentID)
		for name, s := range summary.Alternatives {
			row := &db.ExperimentSummaryRow{
				ExperimentID:    r.experimentID,
				Alternative:     name,
				TotalRuns:       s.Count,
				SuccessCount:    s.SuccessCount,
				SuccessRate:     s.SuccessRate,
				AvgDuration:     s.AvgDuration,
				AvgTokens:       s.AvgTokens,
				AvgLint:         s.AvgLint,
				Timeouts:        s.Timeouts,
				TotalToolCalls:  s.TotalToolCalls,
				FailedToolCalls: s.FailedTools,
				AvgTestsPassed:  s.AvgTestsPassed,
				AvgTestsFailed:  s.AvgTestsFailed,
				PSuccess:        s.PSuccess,
				PDuration:       s.PDuration,
				PTokens:         s.PTokens,
				PLint:           s.PLint,
				PTestsPassed:    s.PTestsPassed,
				PTestsFailed:    s.PTestsFailed,
			}
			if err := r.db.SaveExperimentSummary(row); err != nil {
				log.Printf("Warning: failed to save summary for %s: %v", name, err)
			}
		}
	}

	return results, nil
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

	return exp.ExecutionControl
}

func (r *Runner) runSingle(ctx context.Context, timestamp time.Time, experimentName string, alt config.Alternative, scen config.Scenario, rep int, experimentDir string, timeout time.Duration) Result {
	start := time.Now()

	res := Result{
		Alternative: alt.Name,
		Scenario:    scen.Name,
		Repetition:  rep,
	}

	// Calculate a simple ID or just use Name/Scen/Rep for logging
	jobID := fmt.Sprintf("[%s|%s|#%d]", alt.Name, scen.Name, rep)
	log.Printf("START %s", jobID)

	// Ensure paths are absolute before passing to WorkspaceMgr
	settingsPath := alt.SettingsPath
	if settingsPath != "" {
		if abs, err := filepath.Abs(settingsPath); err == nil {
			settingsPath = abs
		}
	}
	contextFilePath := alt.ContextFilePath
	if contextFilePath != "" {
		if abs, err := filepath.Abs(contextFilePath); err == nil {
			contextFilePath = abs
		}
	}

	wsPath, err := r.WorkspaceMgr.PrepareWorkspace(experimentDir, alt.Name, scen.Name, rep, settingsPath, contextFilePath, alt.PolicyFiles)
	if err != nil {
		res.Error = fmt.Errorf("workspace prep failed: %w", err)
		res.ErrorStr = res.Error.Error()
		return res
	}
	res.Workspace = wsPath

	// Anchor the workspace to prevent Gemini from walking up to tenkai root
	// If go.mod doesn't exist, create a dummy one
	goModPath := filepath.Join(wsPath, "go.mod")
	if _, err := os.Stat(goModPath); os.IsNotExist(err) {
		initCmd := exec.CommandContext(ctx, "go", "mod", "init", "experiment")
		initCmd.Dir = wsPath
		if err := initCmd.Run(); err != nil {
			log.Printf("Warning: failed to init dummy go.mod: %v", err)
		}
	}

	// 1. Prepare Command with 5-minute timeout
	cmdName := alt.Command
	cmdArgs := alt.Args

	// Handle System Prompt File
	// Check if configured, resolve absolute path if needed
	envMap := make(map[string]string)
	for k, v := range alt.Env {
		envMap[k] = v
	}

	if alt.SystemPromptFile != "" {
		// Resolve relative to CWD (or ideally config file but we don't pass that here yet)
		// For now assuming CWD or absolute
		absPath, err := filepath.Abs(alt.SystemPromptFile)
		if err == nil {
			envMap["GEMINI_SYSTEM_MD"] = absPath
		} else {
			log.Printf("Warning: failed to resolve system prompt file %s: %v", alt.SystemPromptFile, err)
		}
	}

	// Create timeout context
	cmdCtx, cancel := context.WithTimeout(ctx, timeout)
	defer cancel()

	cmd := exec.CommandContext(cmdCtx, cmdName, cmdArgs...)
	cmd.Dir = wsPath

	cmd.Env = os.Environ()
	for k, v := range envMap {
		cmd.Env = append(cmd.Env, fmt.Sprintf("%s=%s", k, v))
	}

	// 2. Pipe PROMPT.md to Stdin using Pipe (safer closing)
	promptPath := filepath.Join(wsPath, "PROMPT.md")
	promptFile, err := os.Open(promptPath)
	if err == nil {
		stdin, err := cmd.StdinPipe()
		if err != nil {
			res.Error = fmt.Errorf("failed to create stdin pipe: %w", err)
			promptFile.Close()
			return res
		}

		go func() {
			defer stdin.Close()
			defer promptFile.Close()
			if _, err := io.Copy(stdin, promptFile); err != nil {
				fmt.Printf("Error piping stdin: %v\n", err)
			}
		}()
	} else {
		// If PROMPT.md is missing, this runs without prompt!
		// But it should be there from template copy.
		res.Error = fmt.Errorf("PROMPT.md missing: %w", err)
		res.ErrorStr = res.Error.Error()
		return res
	}

	// 3. Capture Output (Stream JSON expected)
	// Write directly to file to avoid memory buffering issues and allow tailing
	// NEW: Use logsDir for cleaner organization
	logsDir := filepath.Join(experimentDir, "logs") // Derive from experimentDir
	safeAlt := strings.ReplaceAll(alt.Name, " ", "_")
	safeScen := strings.ReplaceAll(scen.Name, " ", "_")
	logFilename := fmt.Sprintf("%s_%s_rep%d", safeAlt, safeScen, rep)

	logPath := filepath.Join(logsDir, logFilename+".jsonl")
	logFile, err := os.Create(logPath)
	if err != nil {
		res.Error = fmt.Errorf("failed to create events log: %w", err)
		res.ErrorStr = res.Error.Error()
		return res
	}
	// Note: explicitly closing below before parsing

	cmd.Stdout = logFile
	// Capture Stderr to file to avoid "zombie pipe" blocking
	stderrPath := filepath.Join(logsDir, logFilename+".stderr.log")
	stderrFile, err := os.Create(stderrPath)
	if err != nil {
		res.Error = fmt.Errorf("failed to create stderr log: %w", err)
		res.ErrorStr = res.Error.Error()
		return res
	}
	// Note: explicitly closing below

	cmd.Stderr = stderrFile

	if err := cmd.Run(); err != nil {
		// Check if timeout
		if cmdCtx.Err() == context.DeadlineExceeded {
			res.Error = fmt.Errorf("execution timeout (5m limit)")
		} else {
			res.Error = fmt.Errorf("execution failed: %w", err)
		}
		res.ErrorStr = res.Error.Error()
		// Don't return yet, we might have logs to parse
	}

	res.Duration = time.Since(start)
	res.Stdout = "" // stdout is in file

	// Close files to ensure they are flushed and readable by parser
	logFile.Close()
	stderrFile.Close()

	// Read stderr content for result struct
	stderrBytes, _ := os.ReadFile(stderrPath)
	res.Stderr = string(stderrBytes)

	// 4. Parse Metrics
	metrics, err := parser.ParseEvents(logPath)

	if err == nil {
		res.AgentMetrics = metrics
	} else {
		log.Printf("Warning: failed to parse metrics from %s: %v", logPath, err)
	}

	// 5. Verify Code (Test & Lint) - skip for timeouts since code is incomplete
	shouldEvaluate := res.Error == nil
	if res.Error != nil && !strings.Contains(res.Error.Error(), "timeout") {
		// Non-timeout errors might still have partial code worth evaluating
		shouldEvaluate = true
	}

	if shouldEvaluate {
		var scenConfig *config.ScenarioConfig

		// Try to resolve absolute path correctly.
		// Actually best way to get path is from config? But config doesn't have path.
		// Re-use logic from manager?
		// Manager knows inputs.
		// Let's assume standard structure: <repo>/scenarios/<name>/scenario.yaml
		// Or try to load from template path.
		// Since we don't have template path handy easily (manager knows),
		// we can check if it exists in Workspace via manager's knowledge?
		// Actually, runSingle knows experimentDir.
		// Let's just try to load from wsPath if it was copied?
		// Manager copied `scenario.yaml`? NOT strictly required by PrepareWorkspace (it reads it).
		// But PrepareWorkspace *doesn't* copy scenario.yaml to workspace unless it's an asset.

		// Let's try to find it in default search path like Manager does: "./scenarios/"+scen.Name
		cwd, _ := os.Getwd()
		possiblePath := filepath.Join(cwd, "scenarios", scen.Name, "scenario.yaml")
		if _, err := os.Stat(possiblePath); err == nil {
			scenConfig, _ = config.LoadScenarioConfig(possiblePath)
		}

		// Read the metrics log to get stdout content for validation
		// Read logPath content
		logContentBytes, _ := os.ReadFile(logPath)
		stdoutContent := string(logContentBytes)

		metrics, valReport, err := r.evaluateCode(ctx, wsPath, scenConfig, stdoutContent)
		if err != nil {
			log.Printf("Evaluation failed: %v", err)
			res.Error = err
			res.ErrorStr = err.Error()
		} else {
			res.EvaluationMetrics = metrics
			if valReport != nil {
				res.IsSuccess = valReport.OverallSuccess
				res.Score = valReport.TotalScore
				jsonBytes, _ := json.Marshal(valReport)
				res.ValidationReport = string(jsonBytes)

				// NEW: Aggregate counts into metrics so they show up in DB columns
				if res.EvaluationMetrics == nil {
					res.EvaluationMetrics = &EvaluationMetrics{}
				}
				res.EvaluationMetrics.TestsPassed = valReport.TestsPassed
				res.EvaluationMetrics.TestsFailed = valReport.TestsFailed
				res.EvaluationMetrics.LintIssues = valReport.LintIssues
			}
		}
	}

	// Finalize IsSuccess using centralized logic
	res.IsSuccess = res.Success()

	// 6. Snapshot Workspace Files
	res.GeneratedFiles = r.captureFiles(wsPath)

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

func (r *Runner) evaluateCode(ctx context.Context, wsPath string, scenConfig *config.ScenarioConfig, stdout string) (*EvaluationMetrics, *ValidationReport, error) {
	// If scenario config exists and has validation rules, use new engine
	if scenConfig != nil && len(scenConfig.Validation) > 0 {
		report, err := r.Validate(ctx, wsPath, scenConfig.Validation, stdout)
		if err != nil {
			return nil, nil, err
		}
		// Return nil metrics for now, relying on ValidationReport
		// We could map Test items to metrics if needed
		return nil, report, nil
	}

	// Legacy evaluation
	eval := &EvaluationMetrics{}

	// 1. Run Tests with JSON output
	// go test -json ./...
	testCmd := exec.CommandContext(ctx, "go", "test", "-json", "./...")
	testCmd.Dir = wsPath
	var testOut bytes.Buffer
	testCmd.Stdout = &testOut
	_ = testCmd.Run()

	// Parse JSON test output
	// Each line is a JSON object: {"Time":"...","Action":"...","Package":"...","Test":"...","Output":"...","Elapsed":...}
	scanner := bufio.NewScanner(strings.NewReader(testOut.String()))
	testMap := make(map[string]*db.TestResult)
	for scanner.Scan() {
		var entry struct {
			Action  string
			Test    string
			Output  string
			Elapsed float64
		}
		if err := json.Unmarshal(scanner.Bytes(), &entry); err != nil {
			continue
		}
		if entry.Test == "" {
			continue
		}

		res, ok := testMap[entry.Test]
		if !ok {
			res = &db.TestResult{Name: entry.Test}
			testMap[entry.Test] = res
		}

		switch entry.Action {
		case "pass":
			res.Status = "PASS"
			res.DurationNS = int64(entry.Elapsed * 1e9)
		case "fail":
			res.Status = "FAIL"
			res.DurationNS = int64(entry.Elapsed * 1e9)
		case "output":
			res.Output += entry.Output
		case "skip":
			res.Status = "SKIP"
		}
	}
	for _, res := range testMap {
		eval.Tests = append(eval.Tests, *res)
		if res.Status == "PASS" {
			eval.TestsPassed++
		} else if res.Status == "FAIL" {
			eval.TestsFailed++
		}
	}

	// 2. Run Linter with JSON output
	// golangci-lint run --out-format json ./...
	lintCmd := exec.CommandContext(ctx, "golangci-lint", "run", "--out-format", "json", "./...")
	lintCmd.Dir = wsPath
	var lintOut bytes.Buffer
	lintCmd.Stdout = &lintOut
	if err := lintCmd.Run(); err != nil {
		if strings.Contains(err.Error(), "executable file not found") {
			// ignore missing lint
		}
	} else {
		// Output is in lintOut
		// Parse
		var result struct {
			Issues []db.LintIssue `json:"Issues"`
		}
		if err := json.Unmarshal(lintOut.Bytes(), &result); err == nil {
			eval.Lints = result.Issues
			eval.LintIssues = len(result.Issues)
		}
	}

	return eval, nil, nil
}

func (r *Runner) parseGolangciJSON(data []byte, eval *EvaluationMetrics) {
	var report struct {
		Issues []struct {
			FromLinter string `json:"FromLinter"`
			Text       string `json:"Text"`
			Pos        struct {
				Filename string `json:"Filename"`
				Line     int    `json:"Line"`
				Column   int    `json:"Column"`
			} `json:"Pos"`
		} `json:"Issues"`
	}
	if err := json.Unmarshal(data, &report); err != nil {
		return
	}
	for _, iss := range report.Issues {
		eval.Lints = append(eval.Lints, db.LintIssue{
			File:    iss.Pos.Filename,
			Line:    iss.Pos.Line,
			Col:     iss.Pos.Column,
			Message: iss.Text,
			RuleID:  iss.FromLinter,
		})
	}
}

func (r *Runner) runGoVet(ctx context.Context, wsPath string, eval *EvaluationMetrics) {
	cmd := exec.CommandContext(ctx, "go", "vet", "./...")
	cmd.Dir = wsPath
	var out bytes.Buffer
	cmd.Stderr = &out // vet writes to stderr
	_ = cmd.Run()

	scanner := bufio.NewScanner(strings.NewReader(out.String()))
	for scanner.Scan() {
		line := scanner.Text()
		// Format: file:line:col: message
		parts := strings.SplitN(line, ":", 4)
		if len(parts) < 4 {
			continue
		}
		ln, _ := strconv.Atoi(parts[1])
		col, _ := strconv.Atoi(parts[2])
		eval.Lints = append(eval.Lints, db.LintIssue{
			File:    parts[0],
			Line:    ln,
			Col:     col,
			Message: strings.TrimSpace(parts[3]),
			RuleID:  "go vet",
		})
	}
}

package models

import "time"

// EvaluationMetrics holds the results of code verification.
type EvaluationMetrics struct {
	TestsPassed int          `json:"tests_passed"`
	TestsFailed int          `json:"tests_failed"`
	LintIssues  int          `json:"lint_issues"`
	Tests       []TestResult `json:"tests,omitempty"`
	Lints       []LintIssue  `json:"lints,omitempty"`
}

// ExperimentProgress tracks the execution progress of an experiment.
type ExperimentProgress struct {
	Completed  int     `json:"completed"`
	Total      int     `json:"total"`
	Percentage float64 `json:"percentage"`
}

// Experiment represents a full agent evaluation experiment.
type Experiment struct {
	ID                int64     `json:"id"`
	Name              string    `json:"name"`
	Timestamp         time.Time `json:"timestamp"`
	ConfigPath        string    `json:"config_path"`
	ReportPath        string    `json:"report_path"`
	ResultsPath       string    `json:"results_path"`
	Status            string    `json:"status"`
	Reps              int       `json:"reps"`
	Concurrent        int       `json:"concurrent"`
	TotalJobs         int       `json:"total_jobs"`
	CompletedJobs     int       `json:"completed_jobs"`
	PID               int       `json:"pid"`
	Description       string    `json:"description"`
	Duration          int64     `json:"duration"` // in nanoseconds
	ConfigContent     string    `json:"config_content"`
	ReportContent     string    `json:"report_content"`
	ExecutionControl  string    `json:"execution_control"`  // Signal: stop
	ExperimentControl string    `json:"experiment_control"` // Statistical reference alternative
	ErrorMessage      string    `json:"error_message"`
	AIAnalysis        string    `json:"ai_analysis"`
	IsLocked          bool      `json:"is_locked"`
	Annotations       string    `json:"annotations"`

	// Derived Metrics (Calculated on read)
	SuccessRate     float64             `json:"success_rate"`
	AvgDuration     float64             `json:"avg_duration"`
	AvgTokens       float64             `json:"avg_tokens"`
	TotalLint       int                 `json:"total_lint"`
	SuccessfulRuns  int                 `json:"successful_runs"`
	NumAlternatives int                 `json:"num_alternatives"`
	Timeout         string              `json:"timeout"`
	Progress        *ExperimentProgress `json:"progress,omitempty"`
}

// ExperimentSummaryRow contains aggregated statistics for an alternative in an experiment.
type ExperimentSummaryRow struct {
	ID              int64   `json:"id"` // Dummy ID for frontend compatibility
	ExperimentID    int64   `json:"experiment_id"`
	Alternative     string  `json:"alternative"`
	TotalRuns       int     `json:"total_runs"`
	SuccessCount    int     `json:"success_count"`
	SuccessRate     float64 `json:"success_rate"`
	AvgDuration     float64 `json:"avg_duration"`
	AvgTokens       float64 `json:"avg_tokens"`
	AvgInputTokens  float64 `json:"avg_input_tokens"`
	AvgOutputTokens float64 `json:"avg_output_tokens"`
	AvgCachedTokens float64 `json:"avg_cached_tokens"`
	AvgLint         float64 `json:"avg_lint"`
	AvgCoverage     float64 `json:"avg_coverage"`
	AvgTestsPassed  float64 `json:"avg_tests_passed"`
	AvgTestsFailed  float64 `json:"avg_tests_failed"`
	Timeouts        int     `json:"timeouts"`
	TotalToolCalls  int     `json:"total_tool_calls"`
	FailedToolCalls int     `json:"failed_tool_calls"`
	// P-values computed by application, not DB
	PSuccess         float64 `json:"p_success"`
	PDuration        float64 `json:"p_duration"`
	PTokens          float64 `json:"p_tokens"`
	PInputTokens     float64 `json:"p_input_tokens"`
	POutputTokens    float64 `json:"p_output_tokens"`
	PCachedTokens    float64 `json:"p_cached_tokens"`
	PLint            float64 `json:"p_lint"`
	PCoverage        float64 `json:"p_coverage"`
	PTestsPassed     float64 `json:"p_tests_passed"`
	PTestsFailed     float64 `json:"p_tests_failed"`
	PTimeout         float64 `json:"p_timeout"`
	PToolCalls       float64 `json:"p_tool_calls"`
	PFailedToolCalls float64 `json:"p_failed_tool_calls"`

	// Effect Sizes (Cohen's d)
	EffectDuration     float64 `json:"effect_duration,omitempty"`
	EffectTokens       float64 `json:"effect_tokens,omitempty"`
	EffectInputTokens  float64 `json:"effect_input_tokens,omitempty"`
	EffectOutputTokens float64 `json:"effect_output_tokens,omitempty"`
	EffectCachedTokens float64 `json:"effect_cached_tokens,omitempty"`
	EffectCoverage     float64 `json:"effect_coverage,omitempty"`

	ToolAnalysis    []ToolAnalysis     `json:"tool_analysis"`
	FailureReasons  map[string]int     `json:"failure_reasons"`
	PFailureReasons map[string]float64 `json:"p_failure_reasons"`
}

// RunResult contains the outcome of a single agent run.
type RunResult struct {
	ID              int64  `json:"id"`
	ExperimentID    int64  `json:"experiment_id"`
	Alternative     string `json:"alternative"`
	Scenario        string `json:"scenario"`
	Repetition      int    `json:"repetition"`
	Duration        int64  `json:"duration"` // in nanoseconds
	Error           string `json:"error"`
	TestsPassed     int    `json:"tests_passed"`
	TestsFailed     int    `json:"tests_failed"`
	LintIssues      int    `json:"lint_issues"`
	RawJSON         string `json:"raw_json"` // still here for safety, but we'll use columns
	TotalTokens     int    `json:"total_tokens"`
	InputTokens     int    `json:"input_tokens"`
	OutputTokens    int    `json:"output_tokens"`
	CachedTokens    int    `json:"cached_tokens"`
	ToolCallsCount  int    `json:"tool_calls_count"`
	FailedToolCalls int    `json:"failed_tool_calls"`
	LoopDetected    bool   `json:"loop_detected"`
	Model           string `json:"model"`
	SessionID       string `json:"session_id"`
	ModelDuration   int64  `json:"model_duration"` // ms
	Status          string `json:"status"`
	Reason          string `json:"reason"` // SUCCESS, FAILED, TIMEOUT, ABORTED
	Stdout          string `json:"stdout"`
	Stderr          string `json:"stderr"`

	IsSuccess        bool   `json:"is_success"`
	ValidationReport string `json:"validation_report"`
}

// TestResult represents a single test execution outcome.
type TestResult struct {
	ID         int64  `json:"id"`
	RunID      int64  `json:"run_id"`
	Name       string `json:"name"`
	Status     string `json:"status"` // PASS, FAIL, SKIP
	DurationNS int64  `json:"duration_ns"`
	Output     string `json:"output"`
}

// LintIssue represents a single linter finding.
type LintIssue struct {
	ID       int64  `json:"id"`
	RunID    int64  `json:"run_id"`
	File     string `json:"file"`
	Line     int    `json:"line"`
	Col      int    `json:"col"`
	Message  string `json:"message"`
	Severity string `json:"severity"`
	RuleID   string `json:"rule_id"`
}

// ToolUsage represents a single tool call event.
type ToolUsage struct {
	ID        int64     `json:"id"`
	RunID     int64     `json:"run_id"`
	Name      string    `json:"name"`
	Args      string    `json:"args"`
	Status    string    `json:"status"`
	Output    string    `json:"output"`
	Error     string    `json:"error"`
	Duration  int64     `json:"duration"` // nanoseconds
	Timestamp time.Time `json:"timestamp"`
}

// Message represents a message exchanged during a run.
type Message struct {
	ID        int64     `json:"id"`
	RunID     int64     `json:"run_id"`
	Role      string    `json:"role"`
	Content   string    `json:"content"`
	Timestamp time.Time `json:"timestamp"`
}

// RunFile represents a file generated or used during a run.
type RunFile struct {
	ID          int64  `json:"id"`
	RunID       int64  `json:"run_id"`
	Path        string `json:"path"`
	Content     string `json:"content"`
	IsGenerated bool   `json:"is_generated"`
}

// ToolAnalysis contains statistical analysis of tool usage.
type ToolAnalysis struct {
	ToolName         string  `json:"tool_name"`
	SuccFailPValue   float64 `json:"succ_fail_p_value"`
	DurationCorr     float64 `json:"duration_corr"`
	TokensCorr       float64 `json:"tokens_corr"`
	CachedTokensCorr float64 `json:"cached_tokens_corr"`
}

// ToolStatRow contains aggregated stats for a specific tool.
type ToolStatRow struct {
	Alternative string  `json:"alternative"`
	ToolName    string  `json:"tool_name"`
	TotalCalls  int     `json:"total_calls"`
	FailedCalls int     `json:"failed_calls"`
	AvgCalls    float64 `json:"avg_calls"`
}

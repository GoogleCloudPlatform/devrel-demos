package models

type ValidationReport struct {
	Success       bool             `json:"success"`
	Details       string           `json:"details"`
	Coverage      float64          `json:"coverage"`
	TestsPassed   int              `json:"tests_passed"`
	TestsFailed   int              `json:"tests_failed"`
	LintIssues    int              `json:"lint_issues"`
	Items         []ValidationItem `json:"items,omitempty"`
	DetailedTests []TestResult     `json:"detailed_tests,omitempty"`
	DetailedLints []LintIssue      `json:"detailed_lints,omitempty"`
}

type ValidationItem struct {
	Status      string `json:"status"` // PASS/FAIL
	Type        string `json:"type"`   // test, lint, command, model
	Details     string `json:"details"`
	Description string `json:"description,omitempty"`
	Command     string `json:"command,omitempty"`
	Input       string `json:"input,omitempty"`
	Output      string `json:"output,omitempty"`
	Error       string `json:"error,omitempty"`
	Definition  string `json:"definition,omitempty"`
}

type RunMetrics struct {
	TestsPassed         int
	TestsFailed         int
	LintIssues          int
	TotalTokens         int
	InputTokens         int
	OutputTokens        int
	CachedTokens        int
	TotalToolCallsCount int
	FailedToolCalls     int
}

type AgentMetrics struct {
	TotalTokens         int
	InputTokens         int
	OutputTokens        int
	CachedTokens        int
	TotalToolCallsCount int
	FailedToolCalls     int
}

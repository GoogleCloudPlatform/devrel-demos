package db

import (
	"database/sql"
	"fmt"
	"time"

	_ "modernc.org/sqlite"
)

type DB struct {
	conn *sql.DB
}

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
	Description       string    `json:"description"`
	Duration          int64     `json:"duration"` // in nanoseconds
	ConfigContent     string    `json:"config_content"`
	ReportContent     string    `json:"report_content"`
	ExecutionControl  string    `json:"execution_control"`  // Signal: pause, stop, resume
	ExperimentControl string    `json:"experiment_control"` // Statistical reference alternative
	ErrorMessage      string    `json:"error_message"`
	AIAnalysis        string    `json:"ai_analysis"`
}

type ExperimentSummaryRow struct {
	ID              int64   `json:"id"`
	ExperimentID    int64   `json:"experiment_id"`
	Alternative     string  `json:"alternative"`
	TotalRuns       int     `json:"total_runs"`
	SuccessCount    int     `json:"success_count"`
	SuccessRate     float64 `json:"success_rate"`
	AvgDuration     float64 `json:"avg_duration"`
	AvgTokens       float64 `json:"avg_tokens"`
	AvgLint         float64 `json:"avg_lint"`
	Timeouts        int     `json:"timeouts"`
	TotalToolCalls  int     `json:"total_tool_calls"`
	FailedToolCalls int     `json:"failed_tool_calls"`
	AvgTestsPassed  float64 `json:"avg_tests_passed"`
	AvgTestsFailed  float64 `json:"avg_tests_failed"`
	PSuccess        float64 `json:"p_success"`
	PDuration       float64 `json:"p_duration"`
	PTokens         float64 `json:"p_tokens"`
	PLint           float64 `json:"p_lint"`
	PTestsPassed    float64 `json:"p_tests_passed"`
	PTestsFailed    float64 `json:"p_tests_failed"`
}

type RunResult struct {
	ID               int64  `json:"id"`
	ExperimentID     int64  `json:"experiment_id"`
	Alternative      string `json:"alternative"`
	Scenario         string `json:"scenario"`
	Repetition       int    `json:"repetition"`
	Duration         int64  `json:"duration"` // in nanoseconds
	Error            string `json:"error"`
	TestsPassed      int    `json:"tests_passed"`
	TestsFailed      int    `json:"tests_failed"`
	LintIssues       int    `json:"lint_issues"`
	RawJSON          string `json:"raw_json"` // still here for safety, but we'll use columns
	TotalTokens      int    `json:"total_tokens"`
	InputTokens      int    `json:"input_tokens"`
	OutputTokens     int    `json:"output_tokens"`
	ToolCallsCount   int    `json:"tool_calls_count"`
	LoopDetected     bool   `json:"loop_detected"`
	Stdout           string `json:"stdout"`
	Stderr           string `json:"stderr"`
	IsSuccess        bool   `json:"is_success"`
	Score            int    `json:"score"`
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

type Message struct {
	ID        int64     `json:"id"`
	RunID     int64     `json:"run_id"`
	Role      string    `json:"role"`
	Content   string    `json:"content"`
	Timestamp time.Time `json:"timestamp"`
}

type RunFile struct {
	ID          int64  `json:"id"`
	RunID       int64  `json:"run_id"`
	Path        string `json:"path"`
	Content     string `json:"content"`
	IsGenerated bool   `json:"is_generated"`
}

func Open(path string) (*DB, error) {
	conn, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}

	if err := conn.Ping(); err != nil {
		return nil, fmt.Errorf("failed to ping database: %w", err)
	}

	db := &DB{conn: conn}

	// Enable WAL mode for better concurrency and set busy timeout
	if _, err := db.conn.Exec("PRAGMA journal_mode=WAL; PRAGMA busy_timeout = 5000;"); err != nil {
		return nil, fmt.Errorf("failed to configure database: %w", err)
	}

	if err := db.migrate(); err != nil {
		return nil, fmt.Errorf("migration failed: %w", err)
	}

	return db, nil
}

func (db *DB) Close() error {
	return db.conn.Close()
}

func (db *DB) migrate() error {
	queries := []string{
		`CREATE TABLE IF NOT EXISTS experiments (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			name TEXT,
			timestamp DATETIME,
			config_path TEXT,
			report_path TEXT,
			results_path TEXT,
			status TEXT,
			reps INTEGER,
			concurrent INTEGER,
			total_jobs INTEGER DEFAULT 0,
			completed_jobs INTEGER DEFAULT 0,
			error_message TEXT
		);`,
		`CREATE TABLE IF NOT EXISTS run_results (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			experiment_id INTEGER,
			alternative TEXT,
			scenario TEXT,
			repetition INTEGER,
			duration INTEGER,
			error TEXT,
			tests_passed INTEGER,
			tests_failed INTEGER,
			lint_issues INTEGER,
			raw_json TEXT,
			Total_tokens INTEGER DEFAULT 0,
			input_tokens INTEGER DEFAULT 0,
			output_tokens INTEGER DEFAULT 0,
			tool_calls_count INTEGER DEFAULT 0,
			loop_detected BOOLEAN DEFAULT 0,
			stdout TEXT,
			stderr TEXT,
			FOREIGN KEY(experiment_id) REFERENCES experiments(id)
		);`,
		`CREATE TABLE IF NOT EXISTS tool_usage (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			run_id INTEGER,
			name TEXT,
			args TEXT,
			status TEXT,
			output TEXT,
			error TEXT,
			duration INTEGER,
			timestamp DATETIME,
			FOREIGN KEY(run_id) REFERENCES run_results(id)
		);`,
		`CREATE TABLE IF NOT EXISTS messages (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			run_id INTEGER,
			role TEXT,
			content TEXT,
			timestamp DATETIME,
			FOREIGN KEY(run_id) REFERENCES run_results(id)
		);`,
		`CREATE TABLE IF NOT EXISTS run_files (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			run_id INTEGER,
			path TEXT,
			content TEXT,
			is_generated BOOLEAN,
			FOREIGN KEY(run_id) REFERENCES run_results(id)
		);`,
		`CREATE TABLE IF NOT EXISTS test_results (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			run_id INTEGER,
			name TEXT,
			status TEXT,
			duration_ns INTEGER,
			output TEXT,
			FOREIGN KEY(run_id) REFERENCES run_results(id)
		);`,
		`CREATE TABLE IF NOT EXISTS lint_results (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			run_id INTEGER,
			file TEXT,
			line INTEGER,
			col INTEGER,
			message TEXT,
			severity TEXT,
			rule_id TEXT,
			FOREIGN KEY(run_id) REFERENCES run_results(id)
		);`,
		`CREATE UNIQUE INDEX IF NOT EXISTS idx_experiments_name_ts ON experiments(name, timestamp);`,
		`CREATE TABLE IF NOT EXISTS experiment_summaries (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			experiment_id INTEGER NOT NULL,
			alternative TEXT NOT NULL,
			total_runs INTEGER DEFAULT 0,
			success_count INTEGER DEFAULT 0,
			success_rate REAL DEFAULT 0,
			avg_duration REAL DEFAULT 0,
			avg_tokens REAL DEFAULT 0,
			avg_lint REAL DEFAULT 0,
			avg_tests_passed REAL DEFAULT 0,
			avg_tests_failed REAL DEFAULT 0,
			timeouts INTEGER DEFAULT 0,
			total_tool_calls INTEGER DEFAULT 0,
			failed_tool_calls INTEGER DEFAULT 0,
			p_success REAL,
			p_duration REAL,
			p_tokens REAL,
			p_lint REAL,
			p_tests_passed REAL,
			p_tests_failed REAL,
			FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
		);`,
	}

	for _, q := range queries {
		if _, err := db.conn.Exec(q); err != nil {
			return err
		}
	}

	// Schema Migration: Add columns if they don't exist
	migrations := []string{
		"ALTER TABLE experiments ADD COLUMN total_jobs INTEGER DEFAULT 0",
		"ALTER TABLE experiments ADD COLUMN completed_jobs INTEGER DEFAULT 0",
		"ALTER TABLE experiments ADD COLUMN description TEXT",
		"ALTER TABLE experiments ADD COLUMN duration INTEGER DEFAULT 0",
		"ALTER TABLE experiments ADD COLUMN config_content TEXT",
		"ALTER TABLE experiments ADD COLUMN report_content TEXT",
		"ALTER TABLE experiments ADD COLUMN control TEXT",
		"ALTER TABLE run_results ADD COLUMN total_tokens INTEGER DEFAULT 0",
		"ALTER TABLE run_results ADD COLUMN input_tokens INTEGER DEFAULT 0",
		"ALTER TABLE run_results ADD COLUMN output_tokens INTEGER DEFAULT 0",
		"ALTER TABLE run_results ADD COLUMN tool_calls_count INTEGER DEFAULT 0",
		"ALTER TABLE run_results ADD COLUMN loop_detected BOOLEAN DEFAULT 0",
		"ALTER TABLE run_results ADD COLUMN stdout TEXT",
		"ALTER TABLE run_results ADD COLUMN stderr TEXT",
		"ALTER TABLE experiments ADD COLUMN error_message TEXT",
		"ALTER TABLE run_results ADD COLUMN is_success BOOLEAN DEFAULT 0",
		"ALTER TABLE run_results ADD COLUMN score INTEGER DEFAULT 0",
		"ALTER TABLE run_results ADD COLUMN validation_report TEXT",
		"ALTER TABLE experiments ADD COLUMN execution_control TEXT",
		"ALTER TABLE experiments ADD COLUMN experiment_control TEXT",
		"ALTER TABLE experiments ADD COLUMN ai_analysis TEXT",
		"ALTER TABLE experiment_summaries ADD COLUMN avg_tests_passed REAL DEFAULT 0",
		"ALTER TABLE experiment_summaries ADD COLUMN avg_tests_failed REAL DEFAULT 0",
		"ALTER TABLE experiment_summaries ADD COLUMN p_tests_passed REAL",
		"ALTER TABLE experiment_summaries ADD COLUMN p_tests_failed REAL",
	}

	for _, m := range migrations {
		_, _ = db.conn.Exec(m) // Ignore errors if columns already exist
	}

	return nil
}

func (db *DB) CreateExperiment(exp *Experiment) (int64, error) {
	query := `INSERT INTO experiments (name, timestamp, config_path, report_path, results_path, status, reps, concurrent, total_jobs, completed_jobs, description, config_content, execution_control, experiment_control) 
	          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
	res, err := db.conn.Exec(query, exp.Name, exp.Timestamp.Format(time.RFC3339), exp.ConfigPath, exp.ReportPath, exp.ResultsPath, exp.Status, exp.Reps, exp.Concurrent, exp.TotalJobs, exp.CompletedJobs, exp.Description, exp.ConfigContent, exp.ExecutionControl, exp.ExperimentControl)
	if err != nil {
		return 0, err
	}
	return res.LastInsertId()
}

func (db *DB) UpdateExperimentStatus(id int64, status string) error {
	query := `UPDATE experiments SET status = ? WHERE id = ?`
	_, err := db.conn.Exec(query, status, id)
	return err
}

func (db *DB) UpdateExecutionControl(id int64, control string) error {
	query := `UPDATE experiments SET execution_control = ? WHERE id = ?`
	_, err := db.conn.Exec(query, control, id)
	return err
}

func (db *DB) UpdateExperimentError(id int64, err string) error {
	query := `UPDATE experiments SET error_message = ? WHERE id = ?`
	_, e := db.conn.Exec(query, err, id)
	return e
}

func (db *DB) UpdateExperimentDuration(id int64, duration int64) error {
	query := `UPDATE experiments SET duration = ? WHERE id = ?`
	_, err := db.conn.Exec(query, duration, id)
	return err
}

func (db *DB) UpdateExperimentReport(id int64, reportContent string) error {
	query := `UPDATE experiments SET report_content = ? WHERE id = ?`
	_, err := db.conn.Exec(query, reportContent, id)
	return err
}

func (db *DB) UpdateExperimentAIAnalysis(id int64, analysis string) error {
	query := `UPDATE experiments SET ai_analysis = ? WHERE id = ?`
	_, err := db.conn.Exec(query, analysis, id)
	return err
}

func (db *DB) SaveExperimentSummary(s *ExperimentSummaryRow) error {
	query := `INSERT INTO experiment_summaries (experiment_id, alternative, total_runs, success_count, success_rate, avg_duration, avg_tokens, avg_lint, avg_tests_passed, avg_tests_failed, timeouts, total_tool_calls, failed_tool_calls, p_success, p_duration, p_tokens, p_lint, p_tests_passed, p_tests_failed) 
	          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
	_, err := db.conn.Exec(query, s.ExperimentID, s.Alternative, s.TotalRuns, s.SuccessCount, s.SuccessRate, s.AvgDuration, s.AvgTokens, s.AvgLint, s.AvgTestsPassed, s.AvgTestsFailed, s.Timeouts, s.TotalToolCalls, s.FailedToolCalls, s.PSuccess, s.PDuration, s.PTokens, s.PLint, s.PTestsPassed, s.PTestsFailed)
	return err
}

func (db *DB) DeleteExperimentSummaries(experimentID int64) error {
	_, err := db.conn.Exec("DELETE FROM experiment_summaries WHERE experiment_id = ?", experimentID)
	return err
}

func (db *DB) GetExperimentSummaries(experimentID int64) ([]ExperimentSummaryRow, error) {
	query := `SELECT id, experiment_id, alternative, total_runs, success_count, success_rate, avg_duration, avg_tokens, avg_lint, avg_tests_passed, avg_tests_failed, timeouts, total_tool_calls, failed_tool_calls, p_success, p_duration, p_tokens, p_lint, p_tests_passed, p_tests_failed 
	          FROM experiment_summaries WHERE experiment_id = ?`
	rows, err := db.conn.Query(query, experimentID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var summaries []ExperimentSummaryRow
	for rows.Next() {
		var s ExperimentSummaryRow
		err := rows.Scan(&s.ID, &s.ExperimentID, &s.Alternative, &s.TotalRuns, &s.SuccessCount, &s.SuccessRate, &s.AvgDuration, &s.AvgTokens, &s.AvgLint, &s.AvgTestsPassed, &s.AvgTestsFailed, &s.Timeouts, &s.TotalToolCalls, &s.FailedToolCalls, &s.PSuccess, &s.PDuration, &s.PTokens, &s.PLint, &s.PTestsPassed, &s.PTestsFailed)
		if err != nil {
			return nil, err
		}
		summaries = append(summaries, s)
	}
	return summaries, nil
}

func (db *DB) UpdateExperimentProgress(id int64, completed, total int) error {
	query := `UPDATE experiments SET completed_jobs = ?, total_jobs = ? WHERE id = ?`
	_, err := db.conn.Exec(query, completed, total, id)
	return err
}

func (db *DB) SaveRunResult(res *RunResult) (int64, error) {
	query := `INSERT INTO run_results (experiment_id, alternative, scenario, repetition, duration, error, tests_passed, tests_failed, lint_issues, raw_json, total_tokens, input_tokens, output_tokens, tool_calls_count, loop_detected, stdout, stderr, is_success, score, validation_report) 
	          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
	r, err := db.conn.Exec(query, res.ExperimentID, res.Alternative, res.Scenario, res.Repetition, res.Duration, res.Error, res.TestsPassed, res.TestsFailed, res.LintIssues, res.RawJSON, res.TotalTokens, res.InputTokens, res.OutputTokens, res.ToolCallsCount, res.LoopDetected, res.Stdout, res.Stderr, res.IsSuccess, res.Score, res.ValidationReport)
	if err != nil {
		return 0, err
	}
	return r.LastInsertId()
}

func (db *DB) SaveToolUsage(tu *ToolUsage) error {
	query := `INSERT INTO tool_usage (run_id, name, args, status, output, error, duration, timestamp) 
	          VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
	_, err := db.conn.Exec(query, tu.RunID, tu.Name, tu.Args, tu.Status, tu.Output, tu.Error, tu.Duration, tu.Timestamp.Format(time.RFC3339))
	return err
}

func (db *DB) SaveMessage(m *Message) error {
	query := `INSERT INTO messages (run_id, role, content, timestamp) 
	          VALUES (?, ?, ?, ?)`
	_, err := db.conn.Exec(query, m.RunID, m.Role, m.Content, m.Timestamp.Format(time.RFC3339))
	return err
}

func (db *DB) SaveRunFile(f *RunFile) error {
	query := `INSERT INTO run_files (run_id, path, content, is_generated) 
	          VALUES (?, ?, ?, ?)`
	_, err := db.conn.Exec(query, f.RunID, f.Path, f.Content, f.IsGenerated)
	return err
}

func (db *DB) SaveTestResults(results []TestResult) error {
	query := `INSERT INTO test_results (run_id, name, status, duration_ns, output) VALUES (?, ?, ?, ?, ?)`
	for _, res := range results {
		_, err := db.conn.Exec(query, res.RunID, res.Name, res.Status, res.DurationNS, res.Output)
		if err != nil {
			return err
		}
	}
	return nil
}

func (db *DB) SaveLintResults(results []LintIssue) error {
	query := `INSERT INTO lint_results (run_id, file, line, col, message, severity, rule_id) VALUES (?, ?, ?, ?, ?, ?, ?)`
	for _, res := range results {
		_, err := db.conn.Exec(query, res.RunID, res.File, res.Line, res.Col, res.Message, res.Severity, res.RuleID)
		if err != nil {
			return err
		}
	}
	return nil
}

func (db *DB) GetTestResults(runID int64) ([]TestResult, error) {
	query := `SELECT id, run_id, name, status, duration_ns, output FROM test_results WHERE run_id = ?`
	rows, err := db.conn.Query(query, runID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var results []TestResult
	for rows.Next() {
		var r TestResult
		if err := rows.Scan(&r.ID, &r.RunID, &r.Name, &r.Status, &r.DurationNS, &r.Output); err != nil {
			return nil, err
		}
		results = append(results, r)
	}
	return results, nil
}

func (db *DB) GetLintResults(runID int64) ([]LintIssue, error) {
	query := `SELECT id, run_id, file, line, col, message, severity, rule_id FROM lint_results WHERE run_id = ?`
	rows, err := db.conn.Query(query, runID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var results []LintIssue
	for rows.Next() {
		var r LintIssue
		if err := rows.Scan(&r.ID, &r.RunID, &r.File, &r.Line, &r.Col, &r.Message, &r.Severity, &r.RuleID); err != nil {
			return nil, err
		}
		results = append(results, r)
	}
	return results, nil
}

func (db *DB) GetRunFiles(runID int64) ([]*RunFile, error) {
	query := `SELECT id, run_id, path, content, is_generated FROM run_files WHERE run_id = ?`
	rows, err := db.conn.Query(query, runID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var files []*RunFile
	for rows.Next() {
		var f RunFile
		if err := rows.Scan(&f.ID, &f.RunID, &f.Path, &f.Content, &f.IsGenerated); err != nil {
			return nil, err
		}
		files = append(files, &f)
	}
	return files, nil
}

func (db *DB) GetExperimentByID(id int64) (*Experiment, error) {
	query := `SELECT id, name, timestamp, config_path, report_path, results_path, status, reps, concurrent, total_jobs, completed_jobs, description, duration, config_content, report_content, execution_control, experiment_control, error_message, ai_analysis FROM experiments WHERE id = ?`
	row := db.conn.QueryRow(query, id)
	var exp Experiment
	var ts string
	var desc, conf, rep, execCtrl, expCtrl, errMsg, aiAn sql.NullString

	err := row.Scan(&exp.ID, &exp.Name, &ts, &exp.ConfigPath, &exp.ReportPath, &exp.ResultsPath, &exp.Status, &exp.Reps, &exp.Concurrent, &exp.TotalJobs, &exp.CompletedJobs, &desc, &exp.Duration, &conf, &rep, &execCtrl, &expCtrl, &errMsg, &aiAn)
	if err != nil {
		return nil, err
	}
	exp.Timestamp, _ = time.Parse(time.RFC3339, ts)
	exp.Description = desc.String
	exp.ConfigContent = conf.String
	exp.ReportContent = rep.String
	exp.ExecutionControl = execCtrl.String
	exp.ExperimentControl = expCtrl.String
	exp.ErrorMessage = errMsg.String
	exp.AIAnalysis = aiAn.String
	return &exp, nil
}

func (db *DB) GetRunResults(experimentID int64) ([]*RunResult, error) {
	query := `SELECT id, experiment_id, alternative, scenario, repetition, duration, error, tests_passed, tests_failed, lint_issues, raw_json, total_tokens, input_tokens, output_tokens, tool_calls_count, loop_detected, stdout, stderr, is_success, score, validation_report FROM run_results WHERE experiment_id = ?`
	rows, err := db.conn.Query(query, experimentID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var results []*RunResult
	for rows.Next() {
		var r RunResult
		var valReport sql.NullString
		if err := rows.Scan(&r.ID, &r.ExperimentID, &r.Alternative, &r.Scenario, &r.Repetition, &r.Duration, &r.Error, &r.TestsPassed, &r.TestsFailed, &r.LintIssues, &r.RawJSON, &r.TotalTokens, &r.InputTokens, &r.OutputTokens, &r.ToolCallsCount, &r.LoopDetected, &r.Stdout, &r.Stderr, &r.IsSuccess, &r.Score, &valReport); err != nil {
			return nil, err
		}
		r.ValidationReport = valReport.String
		results = append(results, &r)
	}
	return results, nil
}

func (db *DB) DeleteExperiment(id int64) error {
	// First delete run_results
	_, err := db.conn.Exec("DELETE FROM run_results WHERE experiment_id = ?", id)
	if err != nil {
		return err
	}
	// Then delete experiment
	_, err = db.conn.Exec("DELETE FROM experiments WHERE id = ?", id)
	return err
}

func (db *DB) DeleteAllExperiments() error {
	// Delete all results first
	if _, err := db.conn.Exec("DELETE FROM run_results"); err != nil {
		return err
	}
	// Delete all experiments
	_, err := db.conn.Exec("DELETE FROM experiments")
	return err
}

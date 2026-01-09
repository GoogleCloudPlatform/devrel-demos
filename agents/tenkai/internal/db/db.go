package db

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/parser"

	_ "modernc.org/sqlite"
)

type DB struct {
	conn *sql.DB
}

type ExperimentProgress struct {
	Completed  int     `json:"completed"`
	Total      int     `json:"total"`
	Percentage float64 `json:"percentage"`
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
	PID               int       `json:"pid"`
	Description       string    `json:"description"`
	Duration          int64     `json:"duration"` // in nanoseconds
	ConfigContent     string    `json:"config_content"`
	ReportContent     string    `json:"report_content"`
	ExecutionControl  string    `json:"execution_control"`  // Signal: stop
	ExperimentControl string    `json:"experiment_control"` // Statistical reference alternative
	ErrorMessage      string    `json:"error_message"`
	AIAnalysis        string    `json:"ai_analysis"`

	// Derived Metrics (Calculated on read)
	SuccessRate    float64             `json:"success_rate"`
	AvgDuration    float64             `json:"avg_duration"`
	AvgTokens      float64             `json:"avg_tokens"`
	TotalLint      int                 `json:"total_lint"`
	SuccessfulRuns int                 `json:"successful_runs"`
	Progress       *ExperimentProgress `json:"progress,omitempty"`
}

type ExperimentSummaryRow struct {
	ID              int64   `json:"id"` // Dummy ID for frontend compatibility
	ExperimentID    int64   `json:"experiment_id"`
	Alternative     string  `json:"alternative"`
	TotalRuns       int     `json:"total_runs"`
	SuccessCount    int     `json:"success_count"`
	SuccessRate     float64 `json:"success_rate"`
	AvgDuration     float64 `json:"avg_duration"`
	AvgTokens       float64 `json:"avg_tokens"`
	AvgLint         float64 `json:"avg_lint"`
	AvgTestsPassed  float64 `json:"avg_tests_passed"`
	AvgTestsFailed  float64 `json:"avg_tests_failed"`
	Timeouts        int     `json:"timeouts"`
	TotalToolCalls  int     `json:"total_tool_calls"`
	FailedToolCalls int     `json:"failed_tool_calls"`
	// P-values computed by application, not DB
	PSuccess     float64 `json:"p_success"`
	PDuration    float64 `json:"p_duration"`
	PTokens      float64 `json:"p_tokens"`
	PLint        float64 `json:"p_lint"`
	PTestsPassed float64 `json:"p_tests_passed"`
	PTestsFailed float64 `json:"p_tests_failed"`
	PTimeout     float64 `json:"p_timeout"`
}

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
	ToolCallsCount  int    `json:"tool_calls_count"`
	FailedToolCalls int    `json:"failed_tool_calls"`
	LoopDetected    bool   `json:"loop_detected"`
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

// EvaluationMetrics holds the results of code verification.
type EvaluationMetrics struct {
	TestsPassed int          `json:"tests_passed"`
	TestsFailed int          `json:"tests_failed"`
	LintIssues  int          `json:"lint_issues"`
	Tests       []TestResult `json:"tests,omitempty"`
	Lints       []LintIssue  `json:"lints,omitempty"`
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
			error_message TEXT,
			pid INTEGER,
			description TEXT,
			duration INTEGER DEFAULT 0,
			config_content TEXT,
			report_content TEXT,
			execution_control TEXT,
			experiment_control TEXT,
			ai_analysis TEXT
			-- Removed cached metrics columns
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
            total_tokens INTEGER DEFAULT 0,
			input_tokens INTEGER DEFAULT 0,
			output_tokens INTEGER DEFAULT 0,
			tool_calls_count INTEGER DEFAULT 0,
			failed_tool_calls INTEGER DEFAULT 0,
			loop_detected BOOLEAN DEFAULT 0,
			stdout TEXT,
			stderr TEXT,
			is_success BOOLEAN DEFAULT 0,
			validation_report TEXT,
			status TEXT,
			reason TEXT,
			FOREIGN KEY(experiment_id) REFERENCES experiments(id)
		);`,
		`CREATE TABLE IF NOT EXISTS run_events (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			run_id INTEGER,
			type TEXT, -- "tool", "message"
			timestamp DATETIME,
			payload TEXT, -- JSON content
			FOREIGN KEY(run_id) REFERENCES run_results(id)
		);`,
		`CREATE VIEW IF NOT EXISTS tool_usage AS 
			SELECT 
				id, 
				run_id, 
				json_extract(payload, '$.name') as name,
				json_extract(payload, '$.args') as args,
				json_extract(payload, '$.status') as status,
				json_extract(payload, '$.output') as output,
				json_extract(payload, '$.error') as error,
				json_extract(payload, '$.duration') as duration,
				timestamp
			FROM run_events 
			WHERE type = 'tool';`,
		`CREATE VIEW IF NOT EXISTS messages AS 
			SELECT 
				id, 
				run_id, 
				json_extract(payload, '$.role') as role,
				json_extract(payload, '$.content') as content,
				timestamp
			FROM run_events 
			WHERE type = 'message';`,
		// We delete experiment_progress_view and experiment_summaries as they are no longer needed/cached
		`DROP VIEW IF EXISTS experiment_progress_view;`,
		`DROP TABLE IF EXISTS experiment_summaries;`,

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
		`CREATE UNIQUE INDEX IF NOT EXISTS idx_run_results_unique_run ON run_results(experiment_id, alternative, scenario, repetition);`,
	}

	for _, q := range queries {
		if _, err := db.conn.Exec(q); err != nil {
			return err
		}
	}
	return nil
}

func (db *DB) CreateExperiment(exp *Experiment) (int64, error) {
	query := `INSERT INTO experiments (name, timestamp, config_path, report_path, results_path, status, reps, concurrent, total_jobs, completed_jobs, description, config_content, execution_control, experiment_control, pid) 
	          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
	res, err := db.conn.Exec(query, exp.Name, exp.Timestamp.Format(time.RFC3339), exp.ConfigPath, exp.ReportPath, exp.ResultsPath, exp.Status, exp.Reps, exp.Concurrent, exp.TotalJobs, exp.CompletedJobs, exp.Description, exp.ConfigContent, exp.ExecutionControl, exp.ExperimentControl, exp.PID)
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

// GetExperimentSummaries removed. Logic moved to application layer (Server/Runner) for real-time calculation with statistical tests.

type GlobalStats struct {
	TotalExperiments int     `json:"total_experiments"`
	TotalRuns        int     `json:"total_runs"`
	AvgSuccessRate   float64 `json:"avg_success_rate"`
}

func (db *DB) GetGlobalStats() (*GlobalStats, error) {
	var stats GlobalStats
	// Simple counts
	db.conn.QueryRow("SELECT COUNT(*) FROM experiments").Scan(&stats.TotalExperiments)
	db.conn.QueryRow("SELECT COUNT(*) FROM run_results").Scan(&stats.TotalRuns)

	// Avg success rate calculated from real-time aggregation of completed runs per experiment
	// This is complex in SQL. Simplified: Avg of Experiment Success Rates?
	// Or Avg of All Runs success?
	// Let's use Avg of All Runs success for simplicity and speed.
	var avg sql.NullFloat64
	db.conn.QueryRow("SELECT AVG(CASE WHEN is_success THEN 1.0 ELSE 0.0 END) * 100 FROM run_results WHERE status = 'COMPLETED'").Scan(&avg)
	stats.AvgSuccessRate = avg.Float64

	return &stats, nil
}

func (db *DB) UpdateExperimentProgress(id int64, completed, total int) error {
	// Only updates the persistent target if needed
	_, err := db.conn.Exec("UPDATE experiments SET completed_jobs = ?, total_jobs = ? WHERE id = ?", completed, total, id)
	return err
}

// UpdateExperimentMetrics removed - No caching allowed

func (db *DB) SaveRunResult(res *RunResult) (int64, error) {
	query := `INSERT INTO run_results (experiment_id, alternative, scenario, repetition, status, reason) 
	          VALUES (?, ?, ?, ?, ?, ?)
	          ON CONFLICT(experiment_id, alternative, scenario, repetition) 
	          DO UPDATE SET status=excluded.status, reason=excluded.reason
	          RETURNING id`
	var id int64
	err := db.conn.QueryRow(query, res.ExperimentID, res.Alternative, res.Scenario, res.Repetition, res.Status, res.Reason).Scan(&id)
	if err != nil {
		return 0, err
	}
	return id, nil
}
func (db *DB) UpdateRunLogs(id int64, stdout, stderr string) error {
	_, err := db.conn.Exec("UPDATE run_results SET stdout = ?, stderr = ? WHERE id = ?", stdout, stderr, id)
	return err
}
func (db *DB) UpdateRunResult(r *RunResult) error {
	query := `UPDATE run_results SET 
        duration=?, error=?, tests_passed=?, tests_failed=?, lint_issues=?, 
        raw_json=?, total_tokens=?, input_tokens=?, output_tokens=?, 
        tool_calls_count=?, failed_tool_calls=?, loop_detected=?, stdout=?, stderr=?, 
        is_success=?, validation_report=?, status=?, reason=?
        WHERE id=?`
	_, err := db.conn.Exec(query,
		r.Duration, r.Error, r.TestsPassed, r.TestsFailed, r.LintIssues,
		r.RawJSON, r.TotalTokens, r.InputTokens, r.OutputTokens,
		r.ToolCallsCount, r.FailedToolCalls, r.LoopDetected, r.Stdout, r.Stderr,
		r.IsSuccess, r.ValidationReport, r.Status, r.Reason,
		r.ID)
	return err
}

func (db *DB) UpdateRunStatus(id int64, status string) error {
	_, err := db.conn.Exec("UPDATE run_results SET status = ? WHERE id = ?", status, id)
	return err
}

func (db *DB) UpdateRunStatusAndReason(id int64, status, reason string) error {
	_, err := db.conn.Exec("UPDATE run_results SET status = ?, reason = ? WHERE id = ?", status, reason, id)
	return err
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

func (db *DB) DeleteToolUsage(runID int64) error {
	_, err := db.conn.Exec("DELETE FROM tool_usage WHERE run_id = ?", runID)
	return err
}
func (db *DB) DeleteMessages(runID int64) error {
	_, err := db.conn.Exec("DELETE FROM messages WHERE run_id = ?", runID)
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

	var results []TestResult = []TestResult{}
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

	var results []LintIssue = []LintIssue{}
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

	var files []*RunFile = []*RunFile{}
	for rows.Next() {
		var f RunFile
		if err := rows.Scan(&f.ID, &f.RunID, &f.Path, &f.Content, &f.IsGenerated); err != nil {
			return nil, err
		}
		files = append(files, &f)
	}
	return files, nil
}
func (db *DB) GetToolUsage(runID int64) ([]ToolUsage, error) {
	query := `SELECT id, run_id, name, args, status, output, error, duration, timestamp FROM tool_usage WHERE run_id = ? ORDER BY timestamp ASC`
	rows, err := db.conn.Query(query, runID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var results []ToolUsage = []ToolUsage{}
	for rows.Next() {
		var tu ToolUsage
		var ts string
		if err := rows.Scan(&tu.ID, &tu.RunID, &tu.Name, &tu.Args, &tu.Status, &tu.Output, &tu.Error, &tu.Duration, &ts); err != nil {
			return nil, err
		}
		tu.Timestamp, _ = time.Parse(time.RFC3339, ts)
		results = append(results, tu)
	}
	return results, nil
}

func (db *DB) GetMessages(runID int64) ([]Message, error) {
	query := `SELECT 
		id, 
		type,
		payload,
		timestamp 
	FROM run_events 
	WHERE run_id = ?
	ORDER BY id ASC`

	rows, err := db.conn.Query(query, runID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var results []Message
	var currentMsg *Message

	for rows.Next() {
		var id int64
		var evtType, payloadStr, tsStr string

		if err := rows.Scan(&id, &evtType, &payloadStr, &tsStr); err != nil {
			return nil, err
		}

		ts, _ := time.Parse(time.RFC3339, tsStr)

		if evtType == "message" {
			var p struct {
				Role    string `json:"role"`
				Content string `json:"content"`
				Delta   bool   `json:"delta"`
			}
			// Best effort parse
			if err := json.Unmarshal([]byte(payloadStr), &p); err == nil {
				if p.Delta && currentMsg != nil && currentMsg.Role == p.Role {
					currentMsg.Content += p.Content
				} else {
					if currentMsg != nil {
						results = append(results, *currentMsg)
					}
					currentMsg = &Message{
						ID:        id,
						RunID:     runID,
						Role:      p.Role,
						Content:   p.Content,
						Timestamp: ts,
					}
				}
				continue
			}
		}

		// Flush current message
		if currentMsg != nil {
			results = append(results, *currentMsg)
			currentMsg = nil
		}

		// Handle specific formatting for tools
		if evtType == "tool_use" || evtType == "tool_result" {
			var evt parser.GeminiEvent
			if err := json.Unmarshal([]byte(payloadStr), &evt); err == nil {
				var contentMap map[string]string
				if evtType == "tool_use" {
					argsBytes, _ := json.Marshal(evt.Params)
					contentMap = map[string]string{
						"name": evt.ToolName,
						"args": string(argsBytes),
					}
				} else { // tool_result
					output := evt.Output
					if output == "" && evt.Error != "" {
						output = evt.Error
					}
					contentMap = map[string]string{
						"status": evt.Status,
						"output": output,
					}
				}
				contentBytes, _ := json.Marshal(contentMap)

				results = append(results, Message{
					ID:        id,
					RunID:     runID,
					Role:      evtType,
					Content:   string(contentBytes),
					Timestamp: ts,
				})
				continue
			}
		}

		// Fallback for everything else (result, error, etc.)
		results = append(results, Message{
			ID:        id,
			RunID:     runID,
			Role:      evtType,
			Content:   payloadStr,
			Timestamp: ts,
		})
	}

	if currentMsg != nil {
		results = append(results, *currentMsg)
	}

	return results, nil
}

func (db *DB) GetExperimentByID(id int64) (*Experiment, error) {
	// Query experiment metadata
	query := `SELECT 
		e.id, e.name, e.timestamp, e.config_path, e.report_path, e.results_path, 
		e.status, e.reps, e.concurrent, e.total_jobs, e.completed_jobs,
		e.description, e.duration, e.config_content, e.report_content, e.execution_control, e.experiment_control, e.error_message, e.ai_analysis, e.pid
		FROM experiments e WHERE e.id = ?`

	row := db.conn.QueryRow(query, id)

	var exp Experiment
	var ts string
	var desc, conf, rep, execCtrl, expCtrl, errMsg, aiAn sql.NullString

	err := row.Scan(
		&exp.ID, &exp.Name, &ts, &exp.ConfigPath, &exp.ReportPath, &exp.ResultsPath,
		&exp.Status, &exp.Reps, &exp.Concurrent, &exp.TotalJobs, &exp.CompletedJobs,
		&desc, &exp.Duration, &conf, &rep, &execCtrl, &expCtrl, &errMsg, &aiAn, &exp.PID,
	)
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

	// Aggregation Query (Real-time)
	aggQuery := `
	SELECT 
		COUNT(*), 
		SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END),
		SUM(CASE WHEN status = 'RUNNING' THEN 1 ELSE 0 END),
		SUM(CASE WHEN status = 'QUEUED' THEN 1 ELSE 0 END),
		SUM(CASE WHEN status = 'ABORTED' THEN 1 ELSE 0 END),
		AVG(CASE WHEN is_success THEN 1.0 ELSE 0.0 END) * 100,
		AVG(CASE WHEN is_success THEN duration ELSE NULL END) / 1000000000.0,
		AVG(CASE WHEN is_success THEN total_tokens ELSE NULL END),
		SUM(lint_issues),
		SUM(CASE WHEN is_success THEN 1 ELSE 0 END)
	FROM run_results WHERE experiment_id = ?`

	var totalActual, completedActual, running, queued, aborted int
	var sRate, aDur, aTok sql.NullFloat64
	var tLint, sRuns sql.NullInt64

	err = db.conn.QueryRow(aggQuery, id).Scan(
		&totalActual, &completedActual, &running, &queued, &aborted,
		&sRate, &aDur, &aTok, &tLint, &sRuns,
	)

	if err == nil {
		// Target total is from experiments table (intended), progress is from actual terminal runs
		// Treat ABORTED as terminal for progress bar
		completed := completedActual + aborted

		if exp.ErrorMessage != "" || aborted > totalActual/2 { // Heuristic if many aborted
			exp.Status = ExperimentStatusAborted
		} else if completed >= exp.TotalJobs && exp.TotalJobs > 0 {
			exp.Status = ExperimentStatusCompleted
		} else {
			exp.Status = ExperimentStatusRunning
		}

		if exp.TotalJobs == 0 {
			exp.Status = "INITIALIZING"
		}

		// Populate Progress using Persistent Target
		exp.Progress = &ExperimentProgress{
			Completed: completed,
			Total:     exp.TotalJobs,
		}
		if exp.TotalJobs > 0 {
			exp.Progress.Percentage = float64(completed) / float64(exp.TotalJobs) * 100
		}

		exp.SuccessRate = sRate.Float64
		exp.AvgDuration = aDur.Float64
		exp.AvgTokens = aTok.Float64
		exp.TotalLint = int(tLint.Int64)
		exp.SuccessfulRuns = int(sRuns.Int64)

	} else {
		// Error querying metrics
		exp.Status = "UNKNOWN"
	}

	return &exp, nil
}
func (db *DB) GetExperiments() ([]Experiment, error) {
	// Aggregate metrics per experiment
	// This query effectively replaces the need for caching columns in the experiments table.
	// Note: We join on run_results to get live status.

	query := `
	SELECT 
		e.id, e.name, e.timestamp, e.status, e.reps, e.concurrent, e.total_jobs,
		COALESCE(e.pid, 0),
		(
			SELECT COUNT(*) FROM run_results r WHERE r.experiment_id = e.id AND r.status IN ('COMPLETED', 'ABORTED')
		) as completed_actual,
		(
			SELECT AVG(CASE WHEN is_success THEN 1.0 ELSE 0.0 END) * 100 FROM run_results r WHERE r.experiment_id = e.id
		) as success_rate,
		(
			SELECT AVG(CASE WHEN is_success THEN duration ELSE NULL END) / 1000000000.0 FROM run_results r WHERE r.experiment_id = e.id
		) as avg_duration,
		(
			SELECT AVG(CASE WHEN is_success THEN total_tokens ELSE NULL END) FROM run_results r WHERE r.experiment_id = e.id
		) as avg_tokens,
		(
			SELECT SUM(lint_issues) FROM run_results r WHERE r.experiment_id = e.id
		) as total_lint,
		(
			SELECT COUNT(*) FROM run_results r WHERE r.experiment_id = e.id AND is_success
		) as successful_runs
	FROM experiments e 
	ORDER BY e.timestamp DESC`

	rows, err := db.conn.Query(query)

	if err != nil {
		return nil, err
	}
	defer rows.Close()

	experiments := []Experiment{} // Initialize as empty slice
	for rows.Next() {
		var exp Experiment
		var ts string
		var sRate, aDur, aTok sql.NullFloat64
		var tLint, sRuns sql.NullInt64
		var completedActual int

		if err := rows.Scan(&exp.ID, &exp.Name, &ts, &exp.Status, &exp.Reps, &exp.Concurrent, &exp.TotalJobs, &exp.PID,
			&completedActual, &sRate, &aDur, &aTok, &tLint, &sRuns); err != nil {
			return nil, err
		}
		exp.Timestamp, _ = time.Parse(time.RFC3339, ts)
		exp.SuccessRate = sRate.Float64
		exp.AvgDuration = aDur.Float64
		exp.AvgTokens = aTok.Float64
		exp.TotalLint = int(tLint.Int64)
		exp.SuccessfulRuns = int(sRuns.Int64)
		exp.CompletedJobs = completedActual // Derived, not stored

		// Populate Progress
		exp.Progress = &ExperimentProgress{
			Completed: exp.CompletedJobs,
			Total:     exp.TotalJobs,
		}
		if exp.TotalJobs > 0 {
			exp.Progress.Percentage = float64(exp.CompletedJobs) / float64(exp.TotalJobs) * 100
		}
		// Derive Status
		if exp.Status == ExperimentStatusCompleted && exp.CompletedJobs < exp.TotalJobs {
			exp.Status = ExperimentStatusRunning
		}

		experiments = append(experiments, exp)
	}
	return experiments, nil
}

func (db *DB) GetRunResults(experimentID int64) ([]*RunResult, error) {
	query := `SELECT id, experiment_id, alternative, scenario, repetition, duration, error, tests_passed, tests_failed, lint_issues, raw_json, total_tokens, input_tokens, output_tokens, tool_calls_count, failed_tool_calls, loop_detected, stdout, stderr, is_success, validation_report, status, reason FROM run_results WHERE experiment_id = ? ORDER BY id ASC`
	rows, err := db.conn.Query(query, experimentID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var results []*RunResult = []*RunResult{}
	for rows.Next() {
		var r RunResult
		var valReport, status, reason, errMsg, stdout, stderr, rawJSON sql.NullString
		var duration, tPassed, tFailed, lIssues, totalTokens, inTokens, outTokens, toolCalls, failedToolCalls, loopDet, isSucc sql.NullInt64

		err := rows.Scan(
			&r.ID, &r.ExperimentID, &r.Alternative, &r.Scenario, &r.Repetition,
			&duration, &errMsg, &tPassed, &tFailed, &lIssues, &rawJSON,
			&totalTokens, &inTokens, &outTokens, &toolCalls, &failedToolCalls, &loopDet,
			&stdout, &stderr, &isSucc, &valReport, &status, &reason,
		)
		if err != nil {
			return nil, err
		}

		r.Duration = duration.Int64
		r.Error = errMsg.String
		r.RawJSON = rawJSON.String
		r.TestsPassed = int(tPassed.Int64)
		r.TestsFailed = int(tFailed.Int64)
		r.LintIssues = int(lIssues.Int64)
		r.TotalTokens = int(totalTokens.Int64)
		r.InputTokens = int(inTokens.Int64)
		r.OutputTokens = int(outTokens.Int64)
		r.ToolCallsCount = int(toolCalls.Int64)
		r.FailedToolCalls = int(failedToolCalls.Int64)
		r.LoopDetected = loopDet.Int64 == 1
		r.Stdout = stdout.String
		r.Stderr = stderr.String
		r.IsSuccess = isSucc.Int64 == 1
		r.ValidationReport = valReport.String
		r.Status = status.String
		r.Reason = reason.String

		// Impute Reason if missing (Data-Oriented Fix for legacy/broken runs)
		if r.Reason == "" && r.Status == "COMPLETED" {
			if r.IsSuccess {
				r.Reason = "SUCCESS"
			} else {
				// If failed but no specific error reason was saved, it implies a validation failure
				// (e.g. coverage check, logical assertion) that didn't crash the runner.
				r.Reason = "FAILED (VALIDATION)"
			}
		}

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

type ToolStatRow struct {
	Alternative string  `json:"alternative"`
	ToolName    string  `json:"tool_name"`
	TotalCalls  int     `json:"total_calls"`
	FailedCalls int     `json:"failed_calls"`
	AvgCalls    float64 `json:"avg_calls"` // Average calls per run
}

func (db *DB) GetToolStats(experimentID int64) ([]ToolStatRow, error) {
	// We need total runs per alternative to calculate average
	// CTE to get total runs
	query := `
	WITH RunCounts AS (
		SELECT alternative, COUNT(*) as total_runs 
		FROM run_results 
		WHERE experiment_id = ? 
		GROUP BY alternative
	)
	SELECT 
		r.alternative, 
		t.name, 
		COUNT(t.id) as total_calls,
		SUM(CASE WHEN t.status != 'success' THEN 1 ELSE 0 END) as failed_calls,
		CAST(COUNT(t.id) AS FLOAT) / rc.total_runs as avg_calls
	FROM tool_usage t
	JOIN run_results r ON t.run_id = r.id
	JOIN RunCounts rc ON r.alternative = rc.alternative
	WHERE r.experiment_id = ?
	GROUP BY r.alternative, t.name
	ORDER BY r.alternative, total_calls DESC
	`
	rows, err := db.conn.Query(query, experimentID, experimentID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	stats := []ToolStatRow{}
	for rows.Next() {

		var s ToolStatRow
		if err := rows.Scan(&s.Alternative, &s.ToolName, &s.TotalCalls, &s.FailedCalls, &s.AvgCalls); err != nil {
			return nil, err
		}
		stats = append(stats, s)
	}
	return stats, nil
}

// Transactional Helper
func (db *DB) WithTransaction(fn func(tx *sql.Tx) error) error {
	tx, err := db.conn.Begin()
	if err != nil {
		return err
	}
	if err := fn(tx); err != nil {
		tx.Rollback()
		return err
	}
	return tx.Commit()
}

// Telemetry Data Structs
type RunTelemetry struct {
	Result      *RunResult
	TestResults []TestResult
	LintResults []LintIssue
}

// SaveRunEvent appends a live event (tool/message) to the run_events table.
func (db *DB) SaveRunEvent(runID int64, eventType string, payload interface{}) error {
	jsonBytes, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	_, err = db.conn.Exec("INSERT INTO run_events (run_id, type, timestamp, payload) VALUES (?, ?, ?, ?)",
		runID, eventType, time.Now(), string(jsonBytes))
	return err
}

// GetRunMetrics calculates aggregated metrics from run_events for a specific run.
func (db *DB) GetRunMetrics(runID int64) (*parser.AgentMetrics, error) {
	metrics := &parser.AgentMetrics{}

	// 1. Tool Calls Count (Total count)
	// AgentMetrics.ToolCalls is a slice, we will populate it below.

	// 2. Token Usage (Sum from result events or cumulative?)
	// Usually 'result' event has the final stats.
	// We search for the last 'result' event.
	var payload string
	err := db.conn.QueryRow("SELECT payload FROM run_events WHERE run_id = ? AND type = 'result' ORDER BY timestamp DESC LIMIT 1", runID).Scan(&payload)
	if err == nil {
		var evt parser.GeminiEvent
		if json.Unmarshal([]byte(payload), &evt) == nil && evt.Stats != nil {
			metrics.TotalTokens = evt.Stats.TotalTokens
			metrics.InputTokens = evt.Stats.InputTokens
			metrics.OutputTokens = evt.Stats.OutputTokens
		}
	} else if err != sql.ErrNoRows {
		// Log error but continue?
	}

	// 3. Reconstruct ToolCalls slice (needed for Runner logic if it uses it for validation?)
	// Runner uses `metrics.ToolCalls` to check `tc.Status != "success"`.
	// So we need to populate it.
	toolRows, err := db.conn.Query(`
		SELECT 
			json_extract(payload, '$.name'),
			json_extract(payload, '$.args'),
			json_extract(payload, '$.status'),
			json_extract(payload, '$.output'),
			json_extract(payload, '$.error')
		FROM run_events WHERE run_id = ? AND type = 'tool'`, runID)
	if err == nil {
		defer toolRows.Close()
		for toolRows.Next() {
			var tc parser.ToolCall
			var name, args, status, output, errStr sql.NullString
			if err := toolRows.Scan(&name, &args, &status, &output, &errStr); err == nil {
				tc.Name = name.String
				tc.Args = args.String
				tc.Status = status.String
				tc.Output = output.String
				tc.Error = errStr.String
				metrics.ToolCalls = append(metrics.ToolCalls, tc)
				if tc.Status != "success" {
					metrics.FailedToolCalls++
				}
			}
			metrics.TotalToolCallsCount = len(metrics.ToolCalls)
		}
	}

	// 4. Check Loop Detection (from errors)
	var loopCount int
	db.conn.QueryRow("SELECT COUNT(*) FROM run_events WHERE run_id = ? AND type = 'error' AND json_extract(payload, '$.message') LIKE '%Loop detected%'", runID).Scan(&loopCount)
	if loopCount > 0 {
		metrics.LoopDetected = true
	}

	return metrics, nil
}

// SaveRunTelemetry saves final run status and test/lint results.
// Note: Tools and Messages are now handled via run_events and views, so we don't save them here.
func (db *DB) SaveRunTelemetry(t *RunTelemetry) error {
	return db.WithTransaction(func(tx *sql.Tx) error {
		// 1. Update Run Result
		if t.Result != nil {
			query := `UPDATE run_results SET 
                                duration=?, error=?, tests_passed=?, tests_failed=?, lint_issues=?, 
                                raw_json=?, total_tokens=?, input_tokens=?, output_tokens=?, 
                                tool_calls_count=?, failed_tool_calls=?, loop_detected=?, stdout=?, stderr=?, 
                                is_success=?, validation_report=?, status=?, reason=?
                                WHERE id=?`
			_, err := tx.Exec(query,
				t.Result.Duration, t.Result.Error, t.Result.TestsPassed, t.Result.TestsFailed, t.Result.LintIssues,
				t.Result.RawJSON, t.Result.TotalTokens, t.Result.InputTokens, t.Result.OutputTokens,
				t.Result.ToolCallsCount, t.Result.FailedToolCalls, t.Result.LoopDetected, t.Result.Stdout, t.Result.Stderr,
				t.Result.IsSuccess, t.Result.ValidationReport, t.Result.Status, t.Result.Reason,
				t.Result.ID)
			if err != nil {
				return fmt.Errorf("failed to update run result (ID %d): %w", t.Result.ID, err)
			}
		}

		runID := t.Result.ID

		// 2. Test Results (Wipe & Replace still needed for structured results until we move them to events)
		if len(t.TestResults) > 0 {
			if _, err := tx.Exec("DELETE FROM test_results WHERE run_id = ?", runID); err != nil {
				return err
			}
			for _, res := range t.TestResults {
				query := `INSERT INTO test_results (run_id, name, status, duration_ns, output) VALUES (?, ?, ?, ?, ?)`
				if _, err := tx.Exec(query, runID, res.Name, res.Status, res.DurationNS, res.Output); err != nil {
					return err
				}
			}
		}

		// 3. Lint Results (Wipe & Replace)
		if len(t.LintResults) > 0 {
			if _, err := tx.Exec("DELETE FROM lint_results WHERE run_id = ?", runID); err != nil {
				return err
			}
			for _, res := range t.LintResults {
				query := `INSERT INTO lint_results (run_id, file, line, col, message, severity, rule_id) VALUES (?, ?, ?, ?, ?, ?, ?)`
				if _, err := tx.Exec(query, runID, res.File, res.Line, res.Col, res.Message, res.Severity, res.RuleID); err != nil {
					return err
				}
			}
		}

		return nil
	})
}

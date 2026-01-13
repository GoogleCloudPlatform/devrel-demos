package db

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db/models"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/parser"
)

// GetRunResults fetches a list of runs with relevant metrics
func (db *DB) GetRunResults(expID int64, limit, offset int) ([]models.RunResult, error) {
	query := `SELECT 
		id, experiment_id, alternative, scenario, repetition, duration, error, 
		tests_passed, tests_failed, lint_issues, total_tokens, input_tokens, output_tokens,
		tool_calls_count, failed_tool_calls, loop_detected, is_success, validation_report, status, reason
		FROM run_results WHERE experiment_id = ? ORDER BY id DESC LIMIT ? OFFSET ?`

	rows, err := db.conn.Query(query, expID, limit, offset)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var results []models.RunResult
	for rows.Next() {
		var r models.RunResult
		var valRep, errStr, reason, status sql.NullString
		var dur, tPass, tFail, lint, tTok, iTok, oTok, tCalls, fCalls sql.NullInt64
		var loop, success sql.NullBool

		err := rows.Scan(
			&r.ID, &r.ExperimentID, &r.Alternative, &r.Scenario, &r.Repetition, &dur, &errStr,
			&tPass, &tFail, &lint, &tTok, &iTok, &oTok,
			&tCalls, &fCalls, &loop, &success, &valRep, &status, &reason,
		)
		if err != nil {
			return nil, err
		}
		r.Duration = dur.Int64
		r.ValidationReport = valRep.String
		r.Error = errStr.String
		r.Status = status.String
		r.Reason = reason.String

		r.TestsPassed = int(tPass.Int64)
		r.TestsFailed = int(tFail.Int64)
		r.LintIssues = int(lint.Int64)
		r.TotalTokens = int(tTok.Int64)
		r.InputTokens = int(iTok.Int64)
		r.OutputTokens = int(oTok.Int64)
		r.ToolCallsCount = int(tCalls.Int64)
		r.FailedToolCalls = int(fCalls.Int64)
		r.LoopDetected = loop.Bool
		r.IsSuccess = success.Bool

		results = append(results, r)
	}
	return results, nil
}

func (db *DB) SaveRunResult(r *models.RunResult) (int64, error) {
	query := `INSERT INTO run_results (experiment_id, alternative, scenario, repetition, status, reason, error) 
			VALUES (?, ?, ?, ?, ?, ?, ?)`
	res, err := db.conn.Exec(query,
		r.ExperimentID, r.Alternative, r.Scenario, r.Repetition, r.Status, r.Reason, r.Error)
	if err != nil {
		return 0, err
	}
	return res.LastInsertId()
}

func (db *DB) UpdateRunStatus(id int64, status string) error {
	_, err := db.conn.Exec("UPDATE run_results SET status = ? WHERE id = ?", status, id)
	return err
}

func (db *DB) UpdateRunLogs(runID int64, stdout, stderr string) error {
	query := `UPDATE run_results SET stdout = ?, stderr = ? WHERE id = ?`
	_, err := db.conn.Exec(query, stdout, stderr, runID)
	return err
}

// Telemetry Logic

type RunTelemetry struct {
	Result      *models.RunResult
	TestResults []models.TestResult
	LintResults []models.LintIssue
}

// WithTransaction executes a function within a transaction
func (db *DB) WithTransaction(fn func(tx *sql.Tx) error) error {
	tx, err := db.conn.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()

	if err := fn(tx); err != nil {
		return err
	}

	return tx.Commit()
}

// SaveRunTelemetry saves final run status and test/lint results.
// Note: Tools and Messages are now handled via run_events and views, so we don't save them here.
func (db *DB) SaveRunTelemetry(t *RunTelemetry) error {
	return db.WithTransaction(func(tx *sql.Tx) error {
		// 1. Update Run Result
		if t.Result != nil {
			query := `UPDATE run_results SET 
                                duration=?, error=?, tests_passed=?, tests_failed=?, lint_issues=?, 
                                total_tokens=?, input_tokens=?, output_tokens=?, 
                                tool_calls_count=?, failed_tool_calls=?, loop_detected=?, stdout=?, stderr=?, 
                                is_success=?, validation_report=?, status=?, reason=?
                                WHERE id=?`
			_, err := tx.Exec(query,
				t.Result.Duration, t.Result.Error, t.Result.TestsPassed, t.Result.TestsFailed, t.Result.LintIssues,
				t.Result.TotalTokens, t.Result.InputTokens, t.Result.OutputTokens,
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

// Event & Artifact Logic

func (db *DB) SaveMessage(m *models.Message) error {
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

func (db *DB) SaveRunFile(f *models.RunFile) error {
	query := `INSERT INTO run_files (run_id, path, content, is_generated) 
	          VALUES (?, ?, ?, ?)`
	_, err := db.conn.Exec(query, f.RunID, f.Path, f.Content, f.IsGenerated)
	return err
}
func (db *DB) SaveRunEvent(runID int64, evtType string, payload any) error {
	jsonBytes, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	query := `INSERT INTO run_events (run_id, type, timestamp, payload) VALUES (?, ?, ?, ?)`
	_, err = db.conn.Exec(query, runID, evtType, time.Now().UTC().Format(time.RFC3339), string(jsonBytes))
	return err
}

func (db *DB) SaveTestResults(results []models.TestResult) error {
	query := `INSERT INTO test_results (run_id, name, status, duration_ns, output) VALUES (?, ?, ?, ?, ?)`
	for _, res := range results {
		_, err := db.conn.Exec(query, res.RunID, res.Name, res.Status, res.DurationNS, res.Output)
		if err != nil {
			return err
		}
	}
	return nil
}

func (db *DB) SaveLintResults(results []models.LintIssue) error {
	query := `INSERT INTO lint_results (run_id, file, line, col, message, severity, rule_id) VALUES (?, ?, ?, ?, ?, ?, ?)`
	for _, res := range results {
		_, err := db.conn.Exec(query, res.RunID, res.File, res.Line, res.Col, res.Message, res.Severity, res.RuleID)
		if err != nil {
			return err
		}
	}
	return nil
}

func (db *DB) GetTestResults(runID int64) ([]models.TestResult, error) {
	query := `SELECT id, run_id, name, status, duration_ns, output FROM test_results WHERE run_id = ?`
	rows, err := db.conn.Query(query, runID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var results []models.TestResult = []models.TestResult{}
	for rows.Next() {
		var r models.TestResult
		if err := rows.Scan(&r.ID, &r.RunID, &r.Name, &r.Status, &r.DurationNS, &r.Output); err != nil {
			return nil, err
		}
		results = append(results, r)
	}
	return results, nil
}

func (db *DB) GetLintResults(runID int64) ([]models.LintIssue, error) {
	query := `SELECT id, run_id, file, line, col, message, severity, rule_id FROM lint_results WHERE run_id = ?`
	rows, err := db.conn.Query(query, runID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var results []models.LintIssue = []models.LintIssue{}
	for rows.Next() {
		var r models.LintIssue
		if err := rows.Scan(&r.ID, &r.RunID, &r.File, &r.Line, &r.Col, &r.Message, &r.Severity, &r.RuleID); err != nil {
			return nil, err
		}
		results = append(results, r)
	}
	return results, nil
}

func (db *DB) GetRunFiles(runID int64) ([]*models.RunFile, error) {
	query := `SELECT id, run_id, path, content, is_generated FROM run_files WHERE run_id = ?`
	rows, err := db.conn.Query(query, runID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var files []*models.RunFile = []*models.RunFile{}
	for rows.Next() {
		var f models.RunFile
		if err := rows.Scan(&f.ID, &f.RunID, &f.Path, &f.Content, &f.IsGenerated); err != nil {
			return nil, err
		}
		files = append(files, &f)
	}
	return files, nil
}
func (db *DB) GetToolUsage(runID int64) ([]models.ToolUsage, error) {
	query := `SELECT id, run_id, name, args, status, output, error, duration, timestamp FROM tool_usage WHERE run_id = ? ORDER BY timestamp ASC`
	rows, err := db.conn.Query(query, runID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var results []models.ToolUsage = []models.ToolUsage{}
	for rows.Next() {
		var tu models.ToolUsage
		var ts string
		if err := rows.Scan(&tu.ID, &tu.RunID, &tu.Name, &tu.Args, &tu.Status, &tu.Output, &tu.Error, &tu.Duration, &ts); err != nil {
			return nil, err
		}
		tu.Timestamp, _ = time.Parse(time.RFC3339, ts)
		results = append(results, tu)
	}
	return results, nil
}

func (db *DB) GetMessages(runID int64, limit, offset int) ([]models.Message, error) {
	query := `SELECT 
		id, 
		type,
		payload,
		timestamp 
	FROM run_events 
	WHERE run_id = ?
	ORDER BY id ASC
	LIMIT ? OFFSET ?`

	rows, err := db.conn.Query(query, runID, limit, offset)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var results []models.Message
	var currentMsg *models.Message

	for rows.Next() {
		var id int64
		var evtType, payloadStr, tsStr string

		if err := rows.Scan(&id, &evtType, &payloadStr, &tsStr); err != nil {
			return nil, err
		}

		ts, _ := time.Parse(time.RFC3339, tsStr)
		results, currentMsg = msgsFromEvent(results, currentMsg, id, runID, evtType, payloadStr, ts)
	}

	if currentMsg != nil {
		results = append(results, *currentMsg)
	}

	return results, nil
}

func msgsFromEvent(acc []models.Message, current *models.Message, id, runID int64, evtType, payload string, ts time.Time) ([]models.Message, *models.Message) {
	if evtType == "message" {
		var p struct {
			Role    string `json:"role"`
			Content string `json:"content"`
			Delta   bool   `json:"delta"`
		}
		if err := json.Unmarshal([]byte(payload), &p); err == nil {
			if p.Delta && current != nil && current.Role == p.Role {
				current.Content += p.Content
				return acc, current
			}
			if current != nil {
				acc = append(acc, *current)
			}
			return acc, &models.Message{
				ID:        id,
				RunID:     runID,
				Role:      p.Role,
				Content:   p.Content,
				Timestamp: ts,
			}
		}
	}

	// Flush current
	if current != nil {
		acc = append(acc, *current)
		current = nil
	}

	if evtType == "tool_use" || evtType == "tool_result" {
		var evt parser.GeminiEvent
		if err := json.Unmarshal([]byte(payload), &evt); err == nil {
			content := ""
			if evtType == "tool_use" {
				argsBytes, _ := json.Marshal(evt.Params)
				content = fmt.Sprintf(`{"name":%q,"args":%s}`, evt.ToolName, argsBytes)
			} else {
				out := evt.Output
				if out == "" && evt.Error != "" {
					out = evt.Error
				}
				content = fmt.Sprintf(`{"status":%q,"output":%q}`, evt.Status, out)
			}
			acc = append(acc, models.Message{
				ID:        id,
				RunID:     runID,
				Role:      evtType,
				Content:   content,
				Timestamp: ts,
			})
			return acc, nil
		}
	}

	acc = append(acc, models.Message{
		ID:        id,
		RunID:     runID,
		Role:      evtType,
		Content:   payload,
		Timestamp: ts,
	})
	return acc, nil
}

// GetRunMetrics calculates aggregated metrics purely from run_events.
// This ensures the DB event log is the Single Source of Truth.
func (db *DB) GetRunMetrics(runID int64) (*parser.AgentMetrics, error) {
	metrics := &parser.AgentMetrics{}

	// 1. Get Tokens and Result status from 'result' event
	// We order by id DESC to get the latest result if multiple exist (unlikely but safe)
	queryResult := `
		SELECT 
			json_extract(payload, '$.stats.total_tokens'),
			json_extract(payload, '$.stats.input_tokens'),
			json_extract(payload, '$.stats.output_tokens'),
			json_extract(payload, '$.status')
		FROM run_events 
		WHERE run_id = ? AND type = 'result'
		ORDER BY id DESC LIMIT 1`

	var tTok, iTok, oTok sql.NullInt64
	var resStatus sql.NullString
	if err := db.conn.QueryRow(queryResult, runID).Scan(&tTok, &iTok, &oTok, &resStatus); err == nil {
		metrics.TotalTokens = int(tTok.Int64)
		metrics.InputTokens = int(iTok.Int64)
		metrics.OutputTokens = int(oTok.Int64)
		metrics.Result = resStatus.String
	}

	// 2. Detect Loops from 'error' events
	queryLoop := `
		SELECT COUNT(*) 
		FROM run_events 
		WHERE run_id = ? AND type = 'error' AND json_extract(payload, '$.message') LIKE '%Loop detected%'`
	var loopCount int
	if err := db.conn.QueryRow(queryLoop, runID).Scan(&loopCount); err == nil && loopCount > 0 {
		metrics.LoopDetected = true
	}

	// 3. Count structured tool calls (stdout)
	queryTools := `
		SELECT 
			COUNT(*),
			SUM(CASE WHEN json_extract(payload, '$.status') != 'success' THEN 1 ELSE 0 END)
		FROM run_events 
		WHERE run_id = ? AND type = 'tool'`

	var totalStructured, failedStructured sql.NullInt64
	db.conn.QueryRow(queryTools, runID).Scan(&totalStructured, &failedStructured)

	// 4. Count stderr tool errors
	queryStderr := `
		SELECT COUNT(*)
		FROM run_events 
		WHERE run_id = ? 
		  AND type = 'error' 
		  AND json_extract(payload, '$.message') LIKE 'Error executing tool %'`
	
	var failedStderr int
	db.conn.QueryRow(queryStderr, runID).Scan(&failedStderr)

	// Aggregate counts
	metrics.FailedToolCalls = int(failedStructured.Int64) + failedStderr
	metrics.TotalToolCallsCount = int(totalStructured.Int64) + failedStderr

	return metrics, nil
}

func (db *DB) UpdateRunStatusAndReason(runID int64, status string, reason string) error {
	query := `UPDATE run_results SET status = ?, reason = ? WHERE id = ?`
	_, err := db.conn.Exec(query, status, reason, runID)
	return err
}

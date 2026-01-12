package db

import (
	"database/sql"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db/models"
)

// GetRunByID fetches a single run result by ID
func (db *DB) GetRunByID(runID int64) (*models.RunResult, error) {
	query := `SELECT 
		id, experiment_id, alternative, scenario, repetition, duration, error, 
		tests_passed, tests_failed, lint_issues, total_tokens, input_tokens, output_tokens,
		tool_calls_count, failed_tool_calls, loop_detected, is_success, validation_report, status, reason
		FROM run_results WHERE id = ?`

	var r models.RunResult
	var valRep, errStr, reason, status sql.NullString
	var dur, tPass, tFail, lint, tTok, iTok, oTok, tCalls, fCalls sql.NullInt64
	var loop, success sql.NullBool

	err := db.conn.QueryRow(query, runID).Scan(
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

	return &r, nil
}

package db

import (
	"fmt"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db/models"
)

// UpdateRunResult updates the core fields of a RunResult.
func (db *DB) UpdateRunResult(r *models.RunResult) error {
	query := `UPDATE run_results SET 
		status=?, reason=?, duration=?, error=?, 
		tests_passed=?, tests_failed=?, lint_issues=?, 
		stdout=?, stderr=?, is_success=?, validation_report=? 
		WHERE id=?`

	_, err := db.conn.Exec(db.Rebind(query),
		r.Status, r.Reason, r.Duration, r.Error,
		r.TestsPassed, r.TestsFailed, r.LintIssues,
		r.Stdout, r.Stderr, r.IsSuccess, r.ValidationReport,
		r.ID)

	if err != nil {
		return fmt.Errorf("failed to update run result %d: %w", r.ID, err)
	}
	return nil
}

// UpdateRunError updates the status, reason, and error message of a run.
func (db *DB) UpdateRunError(id int64, status, reason, errorStr string) error {
	query := `UPDATE run_results SET status = ?, reason = ?, error = ?, is_success = false WHERE id = ?`
	_, err := db.conn.Exec(db.Rebind(query), status, reason, errorStr, id)
	return err
}

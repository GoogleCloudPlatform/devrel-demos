package db

import (
	"database/sql"
	"fmt"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db/models"
)

// GetExperiments fetches all experiments with summary stats
func (db *DB) GetExperiments() ([]models.Experiment, error) {
	query := `
	SELECT 
		e.id, e.name, e.timestamp, e.status, e.reps, e.total_jobs, e.completed_jobs,
		COALESCE(AVG(CASE WHEN r.is_success THEN 1.0 ELSE 0.0 END) * 100, 0) as success_rate,
		COALESCE(AVG(CASE WHEN r.is_success THEN r.duration ELSE NULL END) / 1000000000.0, 0) as avg_duration,
		COALESCE(AVG(CASE WHEN r.is_success THEN r.total_tokens ELSE NULL END), 0) as avg_tokens
	FROM experiments e
	LEFT JOIN run_results r ON e.id = r.experiment_id
	GROUP BY e.id
	ORDER BY e.id DESC`

	rows, err := db.conn.Query(query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var exps []models.Experiment
	for rows.Next() {
		var e models.Experiment
		var ts string
		var sRate, aDur, aTok float64

		if err := rows.Scan(
			&e.ID, &e.Name, &ts, &e.Status, &e.Reps, &e.TotalJobs, &e.CompletedJobs,
			&sRate, &aDur, &aTok,
		); err != nil {
			return nil, err
		}
		e.Timestamp, _ = time.Parse(time.RFC3339, ts)
		e.SuccessRate = sRate
		e.AvgDuration = aDur
		e.AvgTokens = aTok
		exps = append(exps, e)
	}
	return exps, nil
}

// GetExperimentByID fetches detailed experiment data and calculates real-time aggregated stats
func (db *DB) GetExperimentByID(id int64) (*models.Experiment, error) {
	// Query experiment metadata
	query := `SELECT 
		e.id, e.name, e.timestamp, e.config_path, e.report_path, e.results_path, 
		e.status, e.reps, e.concurrent, e.total_jobs, e.completed_jobs,
		e.description, e.duration, e.config_content, e.report_content, e.execution_control, e.experiment_control, e.error_message, e.ai_analysis, e.pid
		FROM experiments e WHERE e.id = ?`

	row := db.conn.QueryRow(query, id)

	var exp models.Experiment
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
		} else if running > 0 {
			exp.Status = ExperimentStatusRunning
		} else {
			// e.g. all queued
			if queued > 0 {
				exp.Status = ExperimentStatusRunning // Or Queued
			}
		}

		exp.SuccessRate = sRate.Float64
		exp.AvgDuration = aDur.Float64
		exp.AvgTokens = aTok.Float64
		exp.TotalLint = int(tLint.Int64)
		exp.SuccessfulRuns = int(sRuns.Int64)

		if exp.TotalJobs > 0 {
			exp.Progress = &models.ExperimentProgress{
				Completed:  completed,
				Total:      exp.TotalJobs,
				Percentage: float64(completed) / float64(exp.TotalJobs) * 100,
			}
		}
	}

	return &exp, nil
}

func (db *DB) CreateExperiment(exp *models.Experiment) (int64, error) {
	query := `INSERT INTO experiments (name, timestamp, config_path, report_path, results_path, status, reps, concurrent, total_jobs, completed_jobs, pid, description, config_content) 
	VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`

	res, err := db.conn.Exec(query,
		exp.Name,
		exp.Timestamp.Format(time.RFC3339),
		exp.ConfigPath,
		exp.ReportPath,
		exp.ResultsPath,
		exp.Status,
		exp.Reps,
		exp.Concurrent,
		exp.TotalJobs,
		exp.CompletedJobs,
		exp.PID,
		exp.Description,
		exp.ConfigContent,
	)
	if err != nil {
		return 0, err
	}
	return res.LastInsertId()
}

func (db *DB) UpdateExperimentStatus(id int64, status string) error {
	_, err := db.conn.Exec("UPDATE experiments SET status = ? WHERE id = ?", status, id)
	return err
}

func (db *DB) UpdateExperimentAIAnalysis(id int64, analysis string) error {
	_, err := db.conn.Exec("UPDATE experiments SET ai_analysis = ? WHERE id = ?", analysis, id)
	return err
}

func (db *DB) UpdateExperimentProgress(id int64, completed, total int) error {
	_, err := db.conn.Exec("UPDATE experiments SET completed_jobs = ?, total_jobs = ? WHERE id = ?", completed, total, id)
	return err
}

func (db *DB) UpdateExecutionControl(expID int64, control string) error {
	_, err := db.conn.Exec("UPDATE experiments SET execution_control = ? WHERE id = ?", control, expID)
	return err
}

func (db *DB) DeleteExperiment(id int64) error {
	tx, err := db.conn.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()

	// Subquery delete for grandchildren
	_, err = tx.Exec("DELETE FROM run_events WHERE run_id IN (SELECT id FROM run_results WHERE experiment_id = ?)", id)
	if err != nil {
		return err
	}
	_, err = tx.Exec("DELETE FROM test_results WHERE run_id IN (SELECT id FROM run_results WHERE experiment_id = ?)", id)
	if err != nil {
		return err
	}
	_, err = tx.Exec("DELETE FROM lint_results WHERE run_id IN (SELECT id FROM run_results WHERE experiment_id = ?)", id)
	if err != nil {
		return err
	}
	_, err = tx.Exec("DELETE FROM run_files WHERE run_id IN (SELECT id FROM run_results WHERE experiment_id = ?)", id)
	if err != nil {
		return err
	}

	_, err = tx.Exec("DELETE FROM run_results WHERE experiment_id = ?", id)
	if err != nil {
		return err
	}
	_, err = tx.Exec("DELETE FROM experiments WHERE id = ?", id)
	if err != nil {
		return err
	}
	return tx.Commit()
}

func (db *DB) DeleteAllExperiments() error {
	// SQLite supports CASCADE delete if configured, but safe to delete children first
	// run_events -> run_results -> experiments
	// Using transaction
	tx, err := db.conn.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()

	// Clear child tables (using generic delete for safety, could truncate if sqlite supported it well)
	if _, err := tx.Exec("DELETE FROM run_events"); err != nil {
		return err
	}
	if _, err := tx.Exec("DELETE FROM tool_usage"); err != nil {
		// view, skip
	}
	if _, err := tx.Exec("DELETE FROM test_results"); err != nil {
		return err
	}
	if _, err := tx.Exec("DELETE FROM lint_results"); err != nil {
		return err
	}
	if _, err := tx.Exec("DELETE FROM run_files"); err != nil {
		return err
	}
	if _, err := tx.Exec("DELETE FROM run_results"); err != nil {
		return err
	}
	if _, err := tx.Exec("DELETE FROM experiments"); err != nil {
		return err
	}

	return tx.Commit()
}

// GetGlobalStats returns aggregate stats across all experiments
func (db *DB) GetGlobalStats() (map[string]interface{}, error) {
	stats := make(map[string]interface{})

	// Total Experiments
	var totalExps int
	if err := db.conn.QueryRow("SELECT COUNT(*) FROM experiments").Scan(&totalExps); err != nil {
		return nil, err
	}
	stats["total_experiments"] = totalExps

	// Total Runs
	var totalRuns int
	if err := db.conn.QueryRow("SELECT COUNT(*) FROM run_results").Scan(&totalRuns); err != nil {
		return nil, err
	}
	stats["total_runs"] = totalRuns

	// Total Duration (hours)
	var totalDurationNS int64
	if err := db.conn.QueryRow("SELECT IFNULL(SUM(duration), 0) FROM run_results").Scan(&totalDurationNS); err != nil {
		return nil, err
	}
	stats["total_duration_hours"] = float64(totalDurationNS) / 1000000000 / 3600

	return stats, nil
}

func (db *DB) GetToolStats(experimentID int64) ([]models.ToolStatRow, error) {
	// We need total runs per alternative to calculate average
	// 1. Get total completed runs per alternative
	runsQuery := `SELECT alternative, count(*) FROM run_results WHERE experiment_id = ? AND status = 'COMPLETED' GROUP BY alternative`
	rows, err := db.conn.Query(runsQuery, experimentID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	runCounts := make(map[string]int)
	for rows.Next() {
		var alt string
		var count int
		if err := rows.Scan(&alt, &count); err == nil {
			runCounts[alt] = count
		}
	}

	// 2. Aggregate tool usage
	// Join tool_usage with runs to group by alternative
	query := `
	SELECT 
		r.alternative,
		t.name,
		COUNT(*) as total,
		SUM(CASE WHEN t.status != 'success' THEN 1 ELSE 0 END) as failed
	FROM tool_usage t
	JOIN run_results r ON t.run_id = r.id
	WHERE r.experiment_id = ?
	GROUP BY r.alternative, t.name
	ORDER BY r.alternative, total DESC`

	rows2, err := db.conn.Query(query, experimentID)
	if err != nil {
		return nil, err
	}
	defer rows2.Close()

	var stats []models.ToolStatRow
	for rows2.Next() {
		var s models.ToolStatRow
		if err := rows2.Scan(&s.Alternative, &s.ToolName, &s.TotalCalls, &s.FailedCalls); err != nil {
			continue
		}
		if count, ok := runCounts[s.Alternative]; ok && count > 0 {
			s.AvgCalls = float64(s.TotalCalls) / float64(count)
		}
		stats = append(stats, s)
	}

	return stats, nil
}

func (db *DB) UpdateExperimentError(experimentID int64, errMsg string) error {
	query := `UPDATE experiments SET error_message = ? WHERE id = ?`
	_, err := db.conn.Exec(query, errMsg, experimentID)
	return err
}

func (db *DB) UpdateExperimentDuration(experimentID int64, duration int64) error {
	query := `UPDATE experiments SET duration = ? WHERE id = ?`
	_, err := db.conn.Exec(query, duration, experimentID)
	return err
}

func (db *DB) UpdateExperimentReport(experimentID int64, reportContent string) error {
	query := `UPDATE experiments SET report_content = ?, report_path = ? WHERE id = ?`
	// Also update report_path to indicate it's stored in DB/virtual
	reportPath := fmt.Sprintf("db://experiments/%d/report.md", experimentID)
	_, err := db.conn.Exec(query, reportContent, reportPath, experimentID)
	return err
}

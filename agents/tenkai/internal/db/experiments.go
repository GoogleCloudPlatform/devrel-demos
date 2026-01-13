package db

import (
	"database/sql"
	"fmt"
	"strings"
	"time"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db/models"
	"gopkg.in/yaml.v3"
)

// GetExperiments fetches all experiments with summary stats
func (db *DB) GetExperiments() ([]models.Experiment, error) {
	query := `
	SELECT 
		e.id, e.name, e.timestamp, e.status, e.reps, e.total_jobs, e.description, e.concurrent, e.config_content, e.experiment_control,
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
		var desc, confContent, expControl sql.NullString

		if err := rows.Scan(
			&e.ID, &e.Name, &ts, &e.Status, &e.Reps, &e.TotalJobs, &desc, &e.Concurrent, &confContent, &expControl,
			&sRate, &aDur, &aTok,
		); err != nil {
			return nil, err
		}
		e.Timestamp, _ = time.Parse(time.RFC3339, ts)
		e.Description = desc.String
		e.ConfigContent = confContent.String
		e.ExperimentControl = expControl.String
		e.SuccessRate = sRate
		e.AvgDuration = aDur
		e.AvgTokens = aTok

		// Aggregation for Progress (Real-time from run_results)
		var completedActual, aborted int
		// Use COALESCE to ensure 0 is returned instead of NULL if no runs exist
		err := db.conn.QueryRow(`
			SELECT 
				COALESCE(SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END), 0),
				COALESCE(SUM(CASE WHEN status = 'ABORTED' THEN 1 ELSE 0 END), 0)
			FROM run_results WHERE experiment_id = ?`, e.ID).Scan(&completedActual, &aborted)

		if err == nil {
			e.CompletedJobs = completedActual + aborted
		} else {
			// If error (shouldn't happen with COALESCE), assume 0 to avoid stale data
			e.CompletedJobs = 0
		}

		// Populate Progress
		if e.TotalJobs > 0 {
			e.Progress = &models.ExperimentProgress{
				Completed:  e.CompletedJobs,
				Total:      e.TotalJobs,
				Percentage: float64(e.CompletedJobs) / float64(e.TotalJobs) * 100,
			}
		}

		// Parse Config for Metadata
		if e.ConfigContent != "" {
			var cfg config.Configuration
			if err := yaml.Unmarshal([]byte(e.ConfigContent), &cfg); err == nil {
				e.NumAlternatives = len(cfg.Alternatives)
				e.Timeout = cfg.Timeout
			}
		}

		exps = append(exps, e)
	}
	return exps, nil
}

// GetExperimentByID fetches detailed experiment data and calculates real-time aggregated stats
func (db *DB) GetExperimentByID(id int64) (*models.Experiment, error) {
	// Query experiment metadata
	query := `SELECT 
		e.id, e.name, e.timestamp, e.config_path, e.report_path, e.results_path, 
		e.status, e.reps, e.concurrent, e.total_jobs,
		e.description, e.duration, e.config_content, e.report_content, e.execution_control, e.experiment_control, e.error_message, e.ai_analysis, e.pid
		FROM experiments e WHERE e.id = ?`

	row := db.conn.QueryRow(query, id)

	var exp models.Experiment
	var ts string
	var desc, conf, rep, execCtrl, expCtrl, errMsg, aiAn sql.NullString

	err := row.Scan(
		&exp.ID, &exp.Name, &ts, &exp.ConfigPath, &exp.ReportPath, &exp.ResultsPath,
		&exp.Status, &exp.Reps, &exp.Concurrent, &exp.TotalJobs,
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
		COALESCE(SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END), 0),
		COALESCE(SUM(CASE WHEN status = 'RUNNING' THEN 1 ELSE 0 END), 0),
		COALESCE(SUM(CASE WHEN status = 'QUEUED' THEN 1 ELSE 0 END), 0),
		COALESCE(SUM(CASE WHEN status = 'ABORTED' THEN 1 ELSE 0 END), 0),
		COALESCE(AVG(CASE WHEN is_success THEN 1.0 ELSE 0.0 END) * 100, 0),
		COALESCE(AVG(CASE WHEN is_success THEN duration ELSE NULL END) / 1000000000.0, 0),
		COALESCE(AVG(CASE WHEN is_success THEN total_tokens ELSE NULL END), 0),
		COALESCE(SUM(lint_issues), 0),
		COALESCE(SUM(CASE WHEN is_success THEN 1 ELSE 0 END), 0)
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

		// If the experiment is not yet marked terminal in DB, check if it finished naturally
		if exp.Status != ExperimentStatusAborted && exp.Status != ExperimentStatusCompleted {
			if completed >= exp.TotalJobs && exp.TotalJobs > 0 {
				exp.Status = ExperimentStatusCompleted
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
	query := `INSERT INTO experiments (name, timestamp, config_path, report_path, results_path, status, reps, concurrent, total_jobs, pid, description, config_content, experiment_control) 
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
		exp.PID,
		exp.Description,
		exp.ConfigContent,
		exp.ExperimentControl,
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
	_, err := db.conn.Exec("UPDATE experiments SET total_jobs = ? WHERE id = ?", total, id)
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

	// Stats aggregation map: alternative -> tool -> stats
	statsMap := make(map[string]map[string]*models.ToolStatRow)
	getStat := func(alt, tool string) *models.ToolStatRow {
		if statsMap[alt] == nil {
			statsMap[alt] = make(map[string]*models.ToolStatRow)
		}
		if statsMap[alt][tool] == nil {
			statsMap[alt][tool] = &models.ToolStatRow{
				Alternative: alt,
				ToolName:    tool,
			}
		}
		return statsMap[alt][tool]
	}

	// 2. Aggregate tool usage from standard 'tool_usage' view
	query := `
	SELECT 
		r.alternative,
		t.name,
		COUNT(*) as total,
		SUM(CASE WHEN t.status != 'success' THEN 1 ELSE 0 END) as failed
	FROM tool_usage t
	JOIN run_results r ON t.run_id = r.id
	WHERE r.experiment_id = ?
	GROUP BY r.alternative, t.name`

	rows2, err := db.conn.Query(query, experimentID)
	if err != nil {
		return nil, err
	}
	defer rows2.Close()

	for rows2.Next() {
		var alt, name string
		var total, failed int
		if err := rows2.Scan(&alt, &name, &total, &failed); err == nil {
			s := getStat(alt, name)
			s.TotalCalls += total
			s.FailedCalls += failed
		}
	}

	// 3. Aggregate tool failures from 'error' events (STDERR fallback)
	// Matches pattern: "Error executing tool {TOOL_NAME}:"
	queryErr := `
    SELECT 
        r.alternative,
        json_extract(payload, '$.message')
    FROM run_events e
    JOIN run_results r ON e.run_id = r.id
    WHERE r.experiment_id = ? 
      AND e.type = 'error' 
      AND json_extract(payload, '$.message') LIKE 'Error executing tool %'`

	rows3, err := db.conn.Query(queryErr, experimentID)
	if err != nil {
		return nil, err
	}
	defer rows3.Close()

	for rows3.Next() {
		var alt, msg string
		if err := rows3.Scan(&alt, &msg); err == nil {
			// Parse: "Error executing tool {NAME}: {DETAILS}"
			// prefix len = 21
			if len(msg) > 21 {
				rest := msg[21:]
				parts := strings.SplitN(rest, ":", 2)
				if len(parts) > 0 {
					toolName := strings.TrimSpace(parts[0])
					s := getStat(alt, toolName)
					s.TotalCalls++
					s.FailedCalls++
				}
			}
		}
	}

	// 4. Flatten and calculate averages
	var stats []models.ToolStatRow
	for alt, tools := range statsMap {
		for _, s := range tools {
			if count, ok := runCounts[alt]; ok && count > 0 {
				s.AvgCalls = float64(s.TotalCalls) / float64(count)
			}
			stats = append(stats, *s)
		}
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

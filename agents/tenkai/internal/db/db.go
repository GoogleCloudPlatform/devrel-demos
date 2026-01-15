package db

import (
	"database/sql"
	"fmt"

	_ "modernc.org/sqlite"
)

type DB struct {
	conn *sql.DB
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
	if _, err := db.conn.Exec("PRAGMA journal_mode=WAL; PRAGMA busy_timeout = 5000; PRAGMA synchronous = NORMAL;"); err != nil {
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
			error_message TEXT,
			pid INTEGER,
			description TEXT,
			duration INTEGER DEFAULT 0,
			config_content TEXT,
			report_content TEXT,
			execution_control TEXT,
			experiment_control TEXT,
			ai_analysis TEXT,
			is_locked BOOLEAN DEFAULT 0
		);`,
		// Migration for existing tables
		`ALTER TABLE experiments ADD COLUMN is_locked BOOLEAN DEFAULT 0;`,
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
			// Ignore error for adding existing column
			if len(q) > 5 && q[:5] == "ALTER" {
				continue
			}
			return err
		}
	}
	return nil
}

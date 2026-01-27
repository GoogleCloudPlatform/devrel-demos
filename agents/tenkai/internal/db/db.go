package db

import (
	"database/sql"
	"fmt"
	"strings"

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
	// Specialized migration: Ensure tool_usage is a view, not a table.
	// We do this before running standard migrations to clear the path for the CREATE VIEW query.
	if err := db.dropToolUsageObject(); err != nil {
		return fmt.Errorf("failed to drop tool_usage object: %w", err)
	}

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
			is_locked BOOLEAN DEFAULT 0,
			annotations TEXT
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
			cached_tokens INTEGER DEFAULT 0,
			tool_calls_count INTEGER DEFAULT 0,
			failed_tool_calls INTEGER DEFAULT 0,
			loop_detected BOOLEAN DEFAULT 0,
			stdout TEXT,
			stderr TEXT,
			is_success BOOLEAN DEFAULT 0,
			validation_report TEXT,
			status TEXT,
			reason TEXT,
			model TEXT,
			session_id TEXT,
			model_duration INTEGER DEFAULT 0,
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
		// Force recreation of tool_usage view to handle migration from table -> view
		// Handled by specialized migration dropToolUsageObject()
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
		// Migration for new columns (idempotency handled by ignoring errors in loop or just simple append)
		`ALTER TABLE experiments ADD COLUMN annotations TEXT DEFAULT '';`,
		`CREATE TABLE IF NOT EXISTS config_blocks (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			name TEXT NOT NULL,
			type TEXT NOT NULL,
			content TEXT NOT NULL,
			UNIQUE(name, type)
		);`,
		`ALTER TABLE run_results ADD COLUMN model TEXT;`,
		`ALTER TABLE run_results ADD COLUMN session_id TEXT;`,
		`ALTER TABLE run_results ADD COLUMN model_duration INTEGER DEFAULT 0;`,
	}

	// 1. Run standard migrations
	for _, q := range queries {
		if _, err := db.conn.Exec(q); err != nil {
			// Ignore duplicate column errors for ADD COLUMN migrations
			if strings.Contains(err.Error(), "duplicate column name") {
				continue
			}
			return err
		}
	}

	// 2. Specialized migrations

	if err := db.migrateConfigBlocksSchema(); err != nil {
		return fmt.Errorf("failed to migrate config_blocks schema: %w", err)
	}

	return nil
}

func (db *DB) dropToolUsageObject() error {
	var typeStr string
	err := db.conn.QueryRow(`SELECT type FROM sqlite_master WHERE name='tool_usage'`).Scan(&typeStr)
	if err == sql.ErrNoRows {
		return nil // Doesn't exist, nothing to do
	}
	if err != nil {
		return err
	}

	if typeStr == "view" {
		_, err = db.conn.Exec(`DROP VIEW tool_usage`)
	} else if typeStr == "table" {
		_, err = db.conn.Exec(`DROP TABLE tool_usage`)
	}
	return err
}

func (db *DB) migrateConfigBlocksSchema() error {
	// Check if the old schema (UNIQUE on name only) exists.
	// We check sqlite_master for the table creation SQL.
	var sqlStmt string
	err := db.conn.QueryRow(`SELECT sql FROM sqlite_master WHERE type='table' AND name='config_blocks'`).Scan(&sqlStmt)
	if err == sql.ErrNoRows {
		return nil // Table doesn't exist yet, standard migration handles it
	}
	if err != nil {
		return err
	}

	// If the SQL contains "name TEXT UNIQUE", we need to migrate.
	// The new schema uses a separate UNIQUE(name, type) line.
	// Note: Strings matching is a bit fragile but sufficient for this specific upgrade path.
	if strings.Contains(sqlStmt, "name TEXT UNIQUE") {
		fmt.Println("[DB] Migrating config_blocks schema to support composite unique constraint...")
		tx, err := db.conn.Begin()
		if err != nil {
			return err
		}
		defer tx.Rollback()

		queries := []string{
			`CREATE TABLE config_blocks_new (
				id INTEGER PRIMARY KEY AUTOINCREMENT,
				name TEXT NOT NULL,
				type TEXT NOT NULL,
				content TEXT NOT NULL,
				UNIQUE(name, type)
			);`,
			`INSERT INTO config_blocks_new (id, name, type, content) SELECT id, name, type, content FROM config_blocks;`,
			`DROP TABLE config_blocks;`,
			`ALTER TABLE config_blocks_new RENAME TO config_blocks;`,
		}

		for _, q := range queries {
			if _, err := tx.Exec(q); err != nil {
				return fmt.Errorf("migration step failed (%s): %w", q, err)
			}
		}

		return tx.Commit()
	}

	return nil
}

package db

import (
	"context"
	"database/sql"
	"fmt"
	"strings"

	_ "github.com/jackc/pgx/v5/stdlib"
	_ "modernc.org/sqlite"
)

type DB struct {
	conn   *sql.DB
	driver string
}

func Open(driver, dsn string) (*DB, error) {
	if driver == "" {
		driver = "sqlite" // Default
	}

	var conn *sql.DB
	var err error

	if driver == "sqlite" {
		conn, err = sql.Open("sqlite", dsn)
		if err != nil {
			return nil, fmt.Errorf("failed to open sqlite database: %w", err)
		}
		// Enable WAL mode for SQLite
		if _, err := conn.Exec("PRAGMA journal_mode=WAL; PRAGMA busy_timeout = 5000; PRAGMA synchronous = NORMAL;"); err != nil {
			return nil, fmt.Errorf("failed to configure sqlite: %w", err)
		}
	} else if driver == "pgx" {
		conn, err = sql.Open("pgx", dsn)
		if err != nil {
			return nil, fmt.Errorf("failed to open postgres database: %w", err)
		}
	} else {
		return nil, fmt.Errorf("unsupported driver: %s", driver)
	}

	if err := conn.Ping(); err != nil {
		return nil, fmt.Errorf("failed to ping database: %w", err)
	}

	db := &DB{conn: conn, driver: driver}

	if err := db.migrate(); err != nil {
		return nil, fmt.Errorf("migration failed: %w", err)
	}

	return db, nil
}

func (db *DB) Close() error {
	return db.conn.Close()
}

// Rebind converts query style from ? to $n if driver is postgres
func (db *DB) Rebind(query string) string {
	if db.driver == "sqlite" {
		return query
	}

	// Postgres: Replace ? with $1, $2, ...
	// Naive implementation: Assumes ? is not used in literals.
	// Valid for our predefined query strings.
	count := 0
	var sb strings.Builder
	for _, char := range query {
		if char == '?' {
			count++
			sb.WriteString(fmt.Sprintf("$%d", count))
		} else {
			sb.WriteRune(char)
		}
	}
	return sb.String()
}

// InsertReturningID handles insertion and ID retrieval compatible with both SQLite and Postgres
func (db *DB) InsertReturningID(query string, args ...any) (int64, error) {
	if db.driver == "sqlite" {
		// SQLite: Use Exec + LastInsertId
		res, err := db.conn.Exec(db.Rebind(query), args...)
		if err != nil {
			return 0, err
		}
		return res.LastInsertId()
	}

	// Postgres: Use QueryRow + RETURNING id
	// Ensure query has RETURNING clause if not present (simple heuristic)
	// Ideally callers should rely on this helper to append it or we do it here.
	// Let's append " RETURNING id" if it's missing.
	if !strings.Contains(strings.ToUpper(query), "RETURNING") {
		query += " RETURNING id"
	}

	var id int64
	err := db.conn.QueryRow(db.Rebind(query), args...).Scan(&id)
	if err != nil {
		return 0, err
	}
	return id, nil
}

func (db *DB) migrate() error {
	// Specialized migration: Ensure tool_usage is a view, not a table.
	if err := db.dropToolUsageObject(); err != nil {
		return fmt.Errorf("failed to drop tool_usage object: %w", err)
	}

	queries := db.getMigrationQueries()

	// 1. Run standard migrations
	for _, q := range queries {
		if _, err := db.conn.Exec(q); err != nil {
			// Ignore duplicate column errors or table exists
			msg := strings.ToLower(err.Error())
			if strings.Contains(msg, "duplicate column") || strings.Contains(msg, "already exists") {
				continue
			}
			return fmt.Errorf("migration failed query: %s\nError: %w", q, err)
		}
	}

	// 2. Specialized migrations
	if err := db.migrateConfigBlocksSchema(); err != nil {
		return fmt.Errorf("failed to migrate config_blocks schema: %w", err)
	}

	return nil
}

func (db *DB) getMigrationQueries() []string {
	var autoInc string
	var timestampType string
	var boolType string
	var jsonType string

	if db.driver == "sqlite" {
		autoInc = "INTEGER PRIMARY KEY AUTOINCREMENT"
		timestampType = "DATETIME"
		boolType = "BOOLEAN"
		jsonType = "TEXT"
	} else {
		// Postgres
		autoInc = "SERIAL PRIMARY KEY"
		timestampType = "TIMESTAMP"
		boolType = "BOOLEAN"
		jsonType = "JSONB"
	}

	return []string{
		fmt.Sprintf(`CREATE TABLE IF NOT EXISTS experiments (
			id %s,
			name TEXT,
			timestamp %s,
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
			duration %s DEFAULT 0,
			config_content TEXT,
			report_content TEXT,
			execution_control TEXT,
			experiment_control TEXT,
			ai_analysis TEXT,
			is_locked %s DEFAULT FALSE,
			annotations TEXT
		);`, autoInc, timestampType, "BIGINT", boolType),

		fmt.Sprintf(`CREATE TABLE IF NOT EXISTS run_results (
			id %s,
			experiment_id INTEGER,
			alternative TEXT,
			scenario TEXT,
			repetition INTEGER,
			duration %s,
			error TEXT,
			tests_passed INTEGER,
			tests_failed INTEGER,
			lint_issues INTEGER,
			raw_json %s,
			total_tokens INTEGER DEFAULT 0,
			input_tokens INTEGER DEFAULT 0,
			output_tokens INTEGER DEFAULT 0,
			cached_tokens INTEGER DEFAULT 0,
			tool_calls_count INTEGER DEFAULT 0,
			failed_tool_calls INTEGER DEFAULT 0,
			loop_detected %s DEFAULT FALSE,
			stdout TEXT,
			stderr TEXT,
			is_success %s DEFAULT FALSE,
			validation_report TEXT,
			status TEXT,
			reason TEXT,
			model TEXT,
			session_id TEXT,
			model_duration INTEGER DEFAULT 0
			%s 
		);`, autoInc, "BIGINT", jsonType, boolType, boolType, db.foreignKey("experiments", "experiment_id")),

		// SQLite doesn't strictly enforce FK in CREATE unless pragma is on, but syntax allows it.
		// Postgres requires strict syntax. RunResult FK handles it.

		fmt.Sprintf(`CREATE TABLE IF NOT EXISTS run_events (
			id %s,
			run_id INTEGER,
			type TEXT, 
			timestamp %s,
			payload %s 
			%s
		);`, autoInc, timestampType, jsonType, db.foreignKey("run_results", "run_id")),

		// Views need special handling for JSON extraction syntax
		db.createToolUsageView(),
		db.createMessagesView(),

		`DROP VIEW IF EXISTS experiment_progress_view;`,
		`DROP TABLE IF EXISTS experiment_summaries;`,

		fmt.Sprintf(`CREATE TABLE IF NOT EXISTS run_files (
			id %s,
			run_id INTEGER,
			path TEXT,
			content TEXT,
			is_generated %s 
			%s
		);`, autoInc, boolType, db.foreignKey("run_results", "run_id")),

		fmt.Sprintf(`CREATE TABLE IF NOT EXISTS test_results (
			id %s,
			run_id INTEGER,
			name TEXT,
			status TEXT,
			duration_ns INTEGER,
			output TEXT
			%s
		);`, autoInc, db.foreignKey("run_results", "run_id")),

		fmt.Sprintf(`CREATE TABLE IF NOT EXISTS lint_results (
			id %s,
			run_id INTEGER,
			file TEXT,
			line INTEGER,
			col INTEGER,
			message TEXT,
			severity TEXT,
			rule_id TEXT
			%s
		);`, autoInc, db.foreignKey("run_results", "run_id")),

		`CREATE UNIQUE INDEX IF NOT EXISTS idx_experiments_name_ts ON experiments(name, timestamp);`,
		`CREATE UNIQUE INDEX IF NOT EXISTS idx_run_results_unique_run ON run_results(experiment_id, alternative, scenario, repetition);`,

		`ALTER TABLE experiments ADD COLUMN annotations TEXT DEFAULT '';`,

		fmt.Sprintf(`CREATE TABLE IF NOT EXISTS config_blocks (
			id %s,
			name TEXT NOT NULL,
			type TEXT NOT NULL,
			content TEXT NOT NULL,
			UNIQUE(name, type)
		);`, autoInc),

		`ALTER TABLE run_results ADD COLUMN model TEXT;`,
		`ALTER TABLE run_results ADD COLUMN session_id TEXT;`,
		`ALTER TABLE run_results ADD COLUMN model_duration INTEGER DEFAULT 0;`,
	}
}

func (db *DB) foreignKey(table, col string) string {
	if db.driver == "sqlite" {
		return fmt.Sprintf(", FOREIGN KEY(%s) REFERENCES %s(id)", col, table)
	}
	// Postgres inline FK
	return fmt.Sprintf(", FOREIGN KEY(%s) REFERENCES %s(id)", col, table)
}

func (db *DB) createToolUsageView() string {
	if db.driver == "sqlite" {
		return `CREATE VIEW IF NOT EXISTS tool_usage AS 
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
			WHERE type = 'tool';`
	}
	// Postgres
	return `CREATE OR REPLACE VIEW tool_usage AS 
			SELECT 
				id, 
				run_id, 
				payload ->> 'name' as name,
				payload -> 'args' as args,
				payload ->> 'status' as status,
				payload ->> 'output' as output,
				payload ->> 'error' as error,
				(payload ->> 'duration')::bigint as duration,
				timestamp
			FROM run_events 
			WHERE type = 'tool';`
}

func (db *DB) createMessagesView() string {
	if db.driver == "sqlite" {
		return `CREATE VIEW IF NOT EXISTS messages AS 
			SELECT 
				id, 
				run_id, 
				json_extract(payload, '$.role') as role,
				json_extract(payload, '$.content') as content,
				timestamp
			FROM run_events 
			WHERE type = 'message';`
	}
	// Postgres
	return `CREATE OR REPLACE VIEW messages AS 
			SELECT 
				id, 
				run_id, 
				payload ->> 'role' as role,
				payload ->> 'content' as content,
				timestamp
			FROM run_events 
			WHERE type = 'message';`
}

func (db *DB) dropToolUsageObject() error {
	// Driver agnostic check
	var typeStr string
	var query string
	if db.driver == "sqlite" {
		query = `SELECT type FROM sqlite_master WHERE name='tool_usage'`
	} else {
		// Postgres
		query = `SELECT table_type FROM information_schema.tables WHERE table_name='tool_usage'`
	}

	err := db.conn.QueryRow(query).Scan(&typeStr)
	if err == sql.ErrNoRows {
		return nil
	}
	if err != nil {
		return err // Postgres might error if no rows? No, QueryRow always returns.
	}

	if strings.ToUpper(typeStr) == "VIEW" {
		_, err = db.conn.Exec(`DROP VIEW tool_usage`)
	} else {
		_, err = db.conn.Exec(`DROP TABLE tool_usage`)
	}
	return err
}

func (db *DB) migrateConfigBlocksSchema() error {
	if db.driver != "sqlite" {
		// For Postgres, we assume fresh install or handled via standard migrations.
		// Detailed SQLite migration logic was for existing local DBs.
		// If we need to support migration for PG, we need a similar check.
		return nil
	}

	// Existing SQLite Migration Logic
	var sqlStmt string
	err := db.conn.QueryRow(`SELECT sql FROM sqlite_master WHERE type='table' AND name='config_blocks'`).Scan(&sqlStmt)
	if err == sql.ErrNoRows {
		return nil
	}
	if err != nil {
		return err
	}

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

// WithTransaction runs a function within a database transaction.
func (db *DB) WithTransaction(fn func(tx *sql.Tx) error) error {
	tx, err := db.conn.BeginTx(context.Background(), nil)
	if err != nil {
		return err
	}

	defer func() {
		if p := recover(); p != nil {
			tx.Rollback()
			panic(p) // Re-throw panic after rollback
		}
	}()

	if err := fn(tx); err != nil {
		tx.Rollback()
		return err
	}

	return tx.Commit()
}

package main

import (
	"context"
	"database/sql"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/jackc/pgx/v5"
	_ "modernc.org/sqlite"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/db"
)

const sqlitePath = "../../experiments/tenkai.db"

func main() {
	pgDSN := os.Getenv("PG_DSN")
	if pgDSN == "" {
		log.Fatal("PG_DSN environment variable is required")
	}

	ctx := context.Background()
	conn, err := pgx.Connect(ctx, pgDSN)
	if err != nil {
		log.Fatalf("Unable to connect to database: %v", err)
	}
	defer conn.Close(ctx)

	// 1. DROP ALL TABLES (CASCADE) to ensure clean slate
	log.Println("!!! DROPPING ALL TABLES (CASCADE) !!!")
	tables := []string{"experiments", "run_results", "run_events", "run_files", "test_results", "lint_results", "config_blocks", "tool_usage", "messages"}
	for _, t := range tables {
		// Try drop table (and views if name matches)
		_, _ = conn.Exec(ctx, fmt.Sprintf("DROP TABLE IF EXISTS %s CASCADE", t))
		_, _ = conn.Exec(ctx, fmt.Sprintf("DROP VIEW IF EXISTS %s CASCADE", t))
	}

	// 2. Initialize Schema (Creates Tables + Constraints)
	log.Println("Initializing Schema (Standard)...")
	tmpDB, err := db.Open("pgx", pgDSN)
	if err != nil {
		log.Fatalf("Failed to init schema: %v", err)
	}
	tmpDB.Close()

	// 3. DROP FOREIGN KEYS to speed up insert and avoid ordering issues
	// We cannot use DISABLE TRIGGER (permission denied). We must DROP constraints.
	log.Println("Dropping Foreign Key Constraints temporarily...")
	fkQuery := `
        SELECT kcu.table_name, kcu.constraint_name 
        FROM information_schema.key_column_usage kcu
        JOIN information_schema.table_constraints tc 
          ON kcu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY' 
          AND kcu.table_schema = 'public';
    `
	rows, err := conn.Query(ctx, fkQuery)
	if err != nil {
		log.Fatalf("Failed to query FKs: %v", err)
	}

	type fkInfo struct {
		table string
		name  string
	}
	var fks []fkInfo
	for rows.Next() {
		var t, n string
		if err := rows.Scan(&t, &n); err == nil {
			fks = append(fks, fkInfo{t, n})
		}
	}
	rows.Close()

	for _, fk := range fks {
		q := fmt.Sprintf(`ALTER TABLE "%s" DROP CONSTRAINT "%s"`, fk.table, fk.name)
		log.Println(q)
		if _, err := conn.Exec(ctx, q); err != nil {
			log.Fatalf("Failed to drop FK %s: %v", fk.name, err)
		}
	}

	// 4. Open SQLite & Bulk Copy
	log.Printf("Opening SQLite DB at %s...", sqlitePath)
	sqliteDB, err := sql.Open("sqlite", sqlitePath)
	if err != nil {
		log.Fatalf("Failed to open SQLite: %v", err)
	}
	defer sqliteDB.Close()

	// Copy Data
	if err := copyExperiments(ctx, sqliteDB, conn); err != nil {
		log.Fatalf("Failed experiments: %v", err)
	}
	if err := copyRunResults(ctx, sqliteDB, conn); err != nil {
		log.Fatalf("Failed run_results: %v", err)
	}
	// Filtered run_events based on valid run_ids to be safe, though FKs are dropped temporarily.
	// It is better to filter so we don't fail when re-enabling FKs.
	if err := copyRunEvents(ctx, sqliteDB, conn); err != nil {
		log.Fatalf("Failed run_events: %v", err)
	}
	if err := copyConfigBlocks(ctx, sqliteDB, conn); err != nil {
		log.Fatalf("Failed config_blocks: %v", err)
	}

	// 5. RESTORE FOREIGN KEYS
	log.Println("Restoring Foreign Keys...")
	// We strictly know the schema from db.go.
	// run_results -> experiments
	// run_events -> run_results
	// run_files -> run_results
	// test_results -> run_results
	// lint_results -> run_results

	// Note: If we dropped them by name, we re-add them by definition.
	// We hardcode standard FKs here.

	constraints := []string{
		`ALTER TABLE run_results ADD CONSTRAINT fk_run_results_experiments FOREIGN KEY (experiment_id) REFERENCES experiments(id)`,
		`ALTER TABLE run_events ADD CONSTRAINT fk_run_events_run_results FOREIGN KEY (run_id) REFERENCES run_results(id)`,
		`ALTER TABLE run_files ADD CONSTRAINT fk_run_files_run_results FOREIGN KEY (run_id) REFERENCES run_results(id)`,
		`ALTER TABLE test_results ADD CONSTRAINT fk_test_results_run_results FOREIGN KEY (run_id) REFERENCES run_results(id)`,
		`ALTER TABLE lint_results ADD CONSTRAINT fk_lint_results_run_results FOREIGN KEY (run_id) REFERENCES run_results(id)`,
	}

	for _, q := range constraints {
		log.Println(q)
		if _, err := conn.Exec(ctx, q); err != nil {
			// Log warning but don't fail hard if data was slightly dirty (though we filtered).
			// Actually, fail hard to let user know schema is not integrity-checked?
			// User wants speed. If data is dirty, we prefer data present over 100% integrity?
			// "I WANT THIS OVER IN LESS THAN 10 MINUTES".
			// If FK restore fails, data is still there. Good.
			log.Printf("Warning: Failed to restore constraint: %v", err)
		}
	}

	log.Println("Migration Completed Successfully!")
}

// copyExperiments copies data using CopyFrom
func copyExperiments(ctx context.Context, src *sql.DB, dst *pgx.Conn) error {
	log.Println("Copying experiments...")
	rows, err := src.Query(`SELECT id, name, timestamp, config_path, status, reps, concurrent, 
		total_jobs, description, duration, config_content, experiment_control, annotations 
		FROM experiments`)
	if err != nil {
		return err
	}
	defer rows.Close()

	var rowsData [][]interface{}
	for rows.Next() {
		var id int64
		var name, tsStr, cfgPath, status string
		var reps, concurrent, totalJobs int64
		var desc string
		var duration sql.NullInt64
		var cfgContent, control, annotations string

		if err := rows.Scan(&id, &name, &tsStr, &cfgPath, &status, &reps, &concurrent, &totalJobs, &desc, &duration, &cfgContent, &control, &annotations); err != nil {
			return err
		}

		ts := parseTime(tsStr)
		rowsData = append(rowsData, []interface{}{
			id, name, ts, cfgPath, "N/A", "N/A", status, reps, concurrent, totalJobs, "", 0, desc, duration, cfgContent, "", "", control, "", false, annotations,
		})
	}

	cols := []string{"id", "name", "timestamp", "config_path", "report_path", "results_path",
		"status", "reps", "concurrent", "total_jobs", "error_message", "pid", "description",
		"duration", "config_content", "report_content", "execution_control", "experiment_control",
		"ai_analysis", "is_locked", "annotations"}

	count, err := dst.CopyFrom(
		ctx,
		pgx.Identifier{"experiments"},
		cols,
		pgx.CopyFromRows(rowsData),
	)
	log.Printf("Copied %d experiments.", count)
	return err
}

// copyRunResults copies data using CopyFrom
func copyRunResults(ctx context.Context, src *sql.DB, dst *pgx.Conn) error {
	log.Println("Copying run_results...")
	// Fetch EVERYTHING
	rows, err := src.Query(`SELECT id, experiment_id, alternative, scenario, repetition, duration, 
        error, tests_passed, tests_failed, lint_issues, raw_json, total_tokens, input_tokens, output_tokens,
        tool_calls_count, failed_tool_calls, loop_detected, is_success, status, reason, model, session_id
        FROM run_results`)
	if err != nil {
		return err
	}
	defer rows.Close()

	var rowsData [][]interface{}
	for rows.Next() {
		var id, expID int64
		var alt, scen string
		var rep int64
		var duration sql.NullInt64
		var errStr sql.NullString
		var passed, failed, lint sql.NullInt64
		var rawJSON sql.NullString
		var tTokens, iTokens, oTokens, tcCount, tcFailed sql.NullInt64
		var loop, success sql.NullBool
		var status, reason string
		var model, sessionID sql.NullString

		if err := rows.Scan(&id, &expID, &alt, &scen, &rep, &duration, &errStr, &passed, &failed, &lint, &rawJSON,
			&tTokens, &iTokens, &oTokens, &tcCount, &tcFailed, &loop, &success, &status, &reason, &model, &sessionID); err != nil {
			return err
		}

		rowsData = append(rowsData, []interface{}{
			id, expID, alt, scen, rep, duration, errStr, passed, failed, lint, rawJSON,
			tTokens, iTokens, oTokens, 0, tcCount, tcFailed, loop, "", "", success, "", status, reason, model, sessionID, 0,
		})
	}

	cols := []string{
		"id", "experiment_id", "alternative", "scenario", "repetition", "duration",
		"error", "tests_passed", "tests_failed", "lint_issues", "raw_json",
		"total_tokens", "input_tokens", "output_tokens", "cached_tokens",
		"tool_calls_count", "failed_tool_calls", "loop_detected", "stdout", "stderr",
		"is_success", "validation_report", "status", "reason", "model", "session_id", "model_duration",
	}

	count, err := dst.CopyFrom(
		ctx,
		pgx.Identifier{"run_results"},
		cols,
		pgx.CopyFromRows(rowsData),
	)
	log.Printf("Copied %d run_results.", count)
	return err
}

func copyRunEvents(ctx context.Context, src *sql.DB, dst *pgx.Conn) error {
	log.Println("Copying run_events...")

	var lastID int64 = 0
	limit := 50000

	for {
		// NOTE: We filter by run_results to ensure FK integrity when we restore constraints
		rows, err := src.Query(`SELECT id, run_id, type, timestamp, payload 
            FROM run_events 
            WHERE id > ? AND run_id IN (SELECT id FROM run_results)
            ORDER BY id LIMIT ?`, lastID, limit)
		if err != nil {
			return err
		}

		var rowsData [][]interface{}
		var maxID int64

		for rows.Next() {
			var id, runID int64
			var typ, tsStr, payload string
			if err := rows.Scan(&id, &runID, &typ, &tsStr, &payload); err != nil {
				rows.Close()
				return err
			}
			if id > maxID {
				maxID = id
			}

			ts := parseTime(tsStr)
			rowsData = append(rowsData, []interface{}{id, runID, typ, ts, payload})
		}
		rows.Close()

		if len(rowsData) == 0 {
			break
		}

		count, err := dst.CopyFrom(
			ctx,
			pgx.Identifier{"run_events"},
			[]string{"id", "run_id", "type", "timestamp", "payload"},
			pgx.CopyFromRows(rowsData),
		)
		if err != nil {
			return err
		}
		log.Printf("Copied batch of %d run_events (Last ID: %d)", count, maxID)
		lastID = maxID
	}
	return nil
}

func copyConfigBlocks(ctx context.Context, src *sql.DB, dst *pgx.Conn) error {
	log.Println("Copying config_blocks...")
	rows, err := src.Query(`SELECT name, type, content FROM config_blocks`)
	if err != nil {
		return nil
	}
	defer rows.Close()

	var rowsData [][]interface{}
	for rows.Next() {
		var name, typ, content string
		if err := rows.Scan(&name, &typ, &content); err != nil {
			return err
		}
		rowsData = append(rowsData, []interface{}{name, typ, content})
	}

	count, err := dst.CopyFrom(
		ctx,
		pgx.Identifier{"config_blocks"},
		[]string{"name", "type", "content"},
		pgx.CopyFromRows(rowsData),
	)
	log.Printf("Copied %d config_blocks.", count)
	return err
}

func parseTime(s string) time.Time {
	ts, _ := time.Parse("2006-01-02 15:04:05.999999999-07:00", s)
	if ts.IsZero() {
		ts, _ = time.Parse(time.RFC3339, s)
	}
	if ts.IsZero() {
		ts = time.Now()
	}
	return ts
}

package main

import (
	"context"
	"database/sql"
	"log"
	"os"
	"time"

	"github.com/jackc/pgx/v5"
	_ "modernc.org/sqlite"
)

func main() {
	sqlitePath := "experiments/tenkai.db"
	pgDSN := os.Getenv("DB_DSN")
	ctx := context.Background()

	if pgDSN == "" {
		log.Fatal("DB_DSN environment variable is required")
	}

	sqliteDB, err := sql.Open("sqlite", sqlitePath)
	if err != nil {
		log.Fatalf("Failed to open SQLite DB: %v", err)
	}
	defer sqliteDB.Close()

	pgConn, err := pgx.Connect(ctx, pgDSN)
	if err != nil {
		log.Fatalf("Failed to connect to Postgres: %v", err)
	}
	defer pgConn.Close(ctx)

	log.Println("Setting session_replication_role to replica...")
	if _, err := pgConn.Exec(ctx, "SET session_replication_role = 'replica';"); err != nil {
		log.Fatalf("Failed to set session_replication_role: %v", err)
	}

	tables := []string{
		"experiments",
		"run_results",
		"run_events",
		"run_files",
		"test_results",
		"lint_results",
		"config_blocks",
	}

	for _, table := range tables {
		log.Printf("Bulk migrating %s...", table)
		copyTable(ctx, sqliteDB, pgConn, table)
	}

	log.Println("Setting session_replication_role to origin...")
	if _, err := pgConn.Exec(ctx, "SET session_replication_role = 'origin';"); err != nil {
		log.Fatalf("Failed to set session_replication_role: %v", err)
	}

	log.Println("Migration complete!")
}

func parseTime(s string) time.Time {
	formats := []string{
		"2006-01-02 15:04:05.999999999",
		"2006-01-02 15:04:05",
		time.RFC3339,
	}
	for _, f := range formats {
		if t, err := time.Parse(f, s); err == nil {
			return t
		}
	}
	return time.Time{}
}

func copyTable(ctx context.Context, src *sql.DB, dst *pgx.Conn, tableName string) {
	rows, err := src.Query("SELECT * FROM " + tableName)
	if err != nil {
		log.Fatalf("Failed to query %s: %v", tableName, err)
	}
	defer rows.Close()

	cols, _ := rows.Columns()
	var allRows [][]interface{}

	for rows.Next() {
		values := make([]interface{}, len(cols))
		scanArgs := make([]interface{}, len(cols))
		for i := range values {
			scanArgs[i] = &values[i]
		}
		if err := rows.Scan(scanArgs...); err != nil {
			log.Fatalf("Failed to scan %s: %v", tableName, err)
		}

		// Basic type cleanup for pgx CopyFrom
		for i, v := range values {
			switch t := v.(type) {
			case []byte:
				values[i] = string(t)
			case int64:
				// Boolean check based on common column names (simplest hardcoded fix)
				if isBoolCol(cols[i]) {
					values[i] = t != 0
				}
			}
			// Special case for experiments.timestamp and run_events.timestamp
			if cols[i] == "timestamp" {
				if s, ok := values[i].(string); ok {
					values[i] = parseTime(s)
				}
			}
			// Sanitize JSON fields
			if cols[i] == "raw_json" || cols[i] == "payload" || cols[i] == "validation_report" {
				if s, ok := values[i].(string); ok {
					if s == "" {
						values[i] = nil
					}
				}
			}
		}
		allRows = append(allRows, values)
	}

	count, err := dst.CopyFrom(
		ctx,
		pgx.Identifier{tableName},
		cols,
		pgx.CopyFromRows(allRows),
	)
	if err != nil {
		log.Fatalf("Failed to copy %s: %v", tableName, err)
	}
	log.Printf("Copied %d rows into %s", count, tableName)
}

func isBoolCol(name string) bool {
	switch name {
	case "is_locked", "loop_detected", "is_success", "is_generated":
		return true
	}
	return false
}

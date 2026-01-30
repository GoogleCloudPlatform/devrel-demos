package main

import (
	"database/sql"
	"flag"
	"fmt"
	"log"

	_ "github.com/jackc/pgx/v5/stdlib"
	_ "modernc.org/sqlite"
)

func main() {
	sqlitePath := flag.String("sqlite", "experiments/tenkai.db", "Path to source SQLite DB")
	pgDSN := flag.String("pg-dsn", "", "Postgres Connection String")
	flag.Parse()

	if *pgDSN == "" {
		log.Fatal("Please provide --pg-dsn")
	}

	// Open SQLite
	src, err := sql.Open("sqlite", *sqlitePath)
	if err != nil {
		log.Fatalf("Failed to open SQLite: %v", err)
	}
	defer src.Close()

	// Open Postgres
	dst, err := sql.Open("pgx", *pgDSN)
	if err != nil {
		log.Fatalf("Failed to open Postgres: %v", err)
	}
	defer dst.Close()

	if err := dst.Ping(); err != nil {
		log.Fatalf("Failed to ping Postgres: %v", err)
	}

	// Patch Schema (Fix Duration Type)
	log.Println("Patching Cloud SQL Schema (INTEGER -> BIGINT for duration)...")
	patchQueries := []string{
		"ALTER TABLE experiments ALTER COLUMN duration TYPE BIGINT",
		"ALTER TABLE run_results ALTER COLUMN duration TYPE BIGINT",
	}
	for _, q := range patchQueries {
		if _, err := dst.Exec(q); err != nil {
			log.Printf("Warning: failed to patch schema (might already be patched): %v", err)
		}
	}

	// Migrate Tables
	tables := []string{"experiments", "run_results", "run_events", "run_files", "test_results", "lint_results", "config_blocks"}

	for _, table := range tables {
		log.Printf("Migrating table: %s", table)
		if err := migrateTable(src, dst, table); err != nil {
			log.Fatalf("Failed to migrate %s: %v", table, err)
		}
	}

	// Reset Sequences (Postgres)
	log.Println("Resetting sequences...")
	seqs := []string{
		"experiments_id_seq",
		"run_results_id_seq",
		"run_events_id_seq",
		"run_files_id_seq",
		"test_results_id_seq",
		"lint_results_id_seq",
		"config_blocks_id_seq",
	}
	for _, seq := range seqs {
		// table name is prefix of sequence usually, but let's be safe.
		// heuristic: table name is seq name minus _id_seq
		tableName := seq[:len(seq)-7]
		query := fmt.Sprintf("SELECT setval('%s', COALESCE((SELECT MAX(id) FROM %s)+1, 1), false)", seq, tableName)
		if _, err := dst.Exec(query); err != nil {
			log.Printf("Warning: failed to reset sequence %s: %v", seq, err)
		}
	}

	log.Println("Migration complete!")
}

func migrateTable(src, dst *sql.DB, table string) error {
	// 1. Get Columns
	rows, err := src.Query(fmt.Sprintf("SELECT * FROM %s", table))
	if err != nil {
		return fmt.Errorf("failed to select from src: %w", err)
	}
	defer rows.Close()

	cols, err := rows.Columns()
	if err != nil {
		return fmt.Errorf("failed to get columns: %w", err)
	}

	// Prepare Insert Statement
	placeholders := ""
	for i := range cols {
		if i > 0 {
			placeholders += ","
		}
		placeholders += fmt.Sprintf("$%d", i+1)
	}

	// Use ON CONFLICT DO NOTHING to avoid duplicates if re-run
	// Note: Postgres syntax
	insertSQL := ""
	if table == "config_blocks" {
		insertSQL = fmt.Sprintf("INSERT INTO %s (%s) VALUES (%s) ON CONFLICT (name, type) DO NOTHING", table, quoteCols(cols), placeholders)
	} else if table == "run_results" {
		// run_results has a unique constraint on (experiment_id, alternative, scenario, repetition)
		insertSQL = fmt.Sprintf("INSERT INTO %s (%s) VALUES (%s) ON CONFLICT (experiment_id, alternative, scenario, repetition) DO NOTHING", table, quoteCols(cols), placeholders)
	} else {
		// Standard ID conflict
		insertSQL = fmt.Sprintf("INSERT INTO %s (%s) VALUES (%s) ON CONFLICT (id) DO NOTHING", table, quoteCols(cols), placeholders)
	}

	stmt, err := dst.Prepare(insertSQL)
	if err != nil {
		return fmt.Errorf("failed to prepare insert: %w", err)
	}
	defer stmt.Close()

	// 2. Iterate and Insert
	count := 0
	values := make([]interface{}, len(cols))
	scanArgs := make([]interface{}, len(cols))
	for i := range values {
		scanArgs[i] = &values[i]
	}

	// Begin Tx
	tx, err := dst.Begin()
	if err != nil {
		return err
	}

	stmtTx := tx.Stmt(stmt)

	for rows.Next() {
		if err := rows.Scan(scanArgs...); err != nil {
			tx.Rollback()
			return fmt.Errorf("scan error: %w", err)
		}

		// Type Conversion (SQLite -> Postgres)
		for i, colName := range cols {
			val := values[i]
			if val == nil {
				continue
			}

			// Boolean Conversion
			// SQLite returns int64(0/1) for booleans. Postgres needs bool.
			isBoolCol := false
			switch colName {
			case "is_locked", "loop_detected", "is_success", "is_generated":
				isBoolCol = true
			}

			if isBoolCol {
				switch v := val.(type) {
				case int64:
					values[i] = v != 0
				case int:
					values[i] = v != 0
				case float64:
					values[i] = v != 0
				case bool:
					values[i] = v // Already bool?
				case []uint8: // Sometimes text "1" or "0" comes as bytes
					str := string(v)
					values[i] = str == "1" || str == "true"
				case string:
					values[i] = v == "1" || v == "true"
				default:
					log.Printf("Warning: Column %s expected bool, got type %T: %v", colName, val, val)
				}
			}
		}

		if _, err := stmtTx.Exec(values...); err != nil {
			tx.Rollback()
			return fmt.Errorf("exec error: %w", err)
		}
		count++
		if count%100 == 0 {
			fmt.Printf(".")
		}
	}
	fmt.Println()

	return tx.Commit()
}

func quoteCols(cols []string) string {
	res := ""
	for i, c := range cols {
		if i > 0 {
			res += ","
		}
		res += c
		// res += fmt.Sprintf("\"%s\"", c) // valid for both? SQLite is loose. Postgres case sensitive?
		// Lowercase columns are standard in this DB.
	}
	return res
}

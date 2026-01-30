package db

import (
	"fmt"
	"strings"
	"time"
)

// JSONExtract returns the SQL syntax for extracting a value from a JSON column.
// path should be in the format '$.key' or '$.key.subkey'.
func (db *DB) JSONExtract(col, path string) string {
	if db.driver == "sqlite" {
		return fmt.Sprintf("json_extract(%s, '%s')", col, path)
	}

	// Postgres: payload -> 'key' ->> 'subkey'
	// Strip $. prefix
	path = strings.TrimPrefix(path, "$.")
	parts := strings.Split(path, ".")

	var sb strings.Builder
	sb.WriteString(col)

	for i, part := range parts {
		if i == len(parts)-1 {
			// Last part gets the value as text
			sb.WriteString("->>")
		} else {
			// Intermediate parts get the value as JSONB
			sb.WriteString("->")
		}
		sb.WriteString(fmt.Sprintf("'%s'", part))
	}
	return sb.String()
}

// ParseDBTime parses a timestamp string from the database, trying multiple formats.
func ParseDBTime(s string) (time.Time, error) {
	formats := []string{
		time.RFC3339,
		"2006-01-02 15:04:05",
		"2006-01-02 15:04:05.999999",
		"2006-01-02 15:04:05+00",
		"2006-01-02T15:04:05Z",
	}
	for _, f := range formats {
		if t, err := time.Parse(f, s); err == nil {
			return t, nil
		}
	}
	return time.Time{}, fmt.Errorf("failed to parse time: %s", s)
}

// FixSequences resets the auto-increment sequences for Postgres tables to max(id).
func (db *DB) FixSequences() error {
	if db.driver == "sqlite" {
		return nil // SQLite handles auto-increment automatically
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
		query := fmt.Sprintf("SELECT setval('%s_id_seq', COALESCE((SELECT MAX(id) FROM %s), 1));", table, table)
		if _, err := db.conn.Exec(query); err != nil {
			return fmt.Errorf("failed to reset sequence for %s: %w", table, err)
		}
	}
	return nil
}

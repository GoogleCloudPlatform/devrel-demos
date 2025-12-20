package query

import (
	"bytes"
	"database/sql"
	"strings"
	"testing"

	_ "github.com/mattn/go-sqlite3"
)

func TestExecute(t *testing.T) {
	// Create an in-memory SQLite database
	db, err := sql.Open("sqlite3", ":memory:")
	if err != nil {
		t.Fatalf("Failed to open in-memory database: %v", err)
	}
	defer db.Close()

	// Create a table and insert some data
	schema := `CREATE TABLE test (id INTEGER, name TEXT);`
	if _, err := db.Exec(schema); err != nil {
		t.Fatalf("Failed to create schema: %v", err)
	}

	insert := `INSERT INTO test (id, name) VALUES (1, 'foo'), (2, 'bar');`
	if _, err := db.Exec(insert); err != nil {
		t.Fatalf("Failed to insert data: %v", err)
	}

	// Execute a query and capture the output
	var buf bytes.Buffer
	if err := Execute(&buf, db, "SELECT * FROM test"); err != nil {
		t.Fatalf("Execute failed: %v", err)
	}

	// Define the expected output
	expected := `
+----+------+
| ID | NAME |
+----+------+
|  1 | foo  |
|  2 | bar  |
+----+------+
`
	// Trim whitespace for a more robust comparison
	got := strings.TrimSpace(buf.String())
	want := strings.TrimSpace(expected)

	if got != want {
		t.Errorf("Execute() got = %v, want %v", got, want)
	}
}

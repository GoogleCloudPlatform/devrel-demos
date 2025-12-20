package shell

import (
	"bytes"
	"context"
	"database/sql"
	"io"
	"strings"
	"sync"
	"testing"

	_ "github.com/mattn/go-sqlite3"
)

func TestPrompt(t *testing.T) {
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
	insert := `INSERT INTO test (id, name) VALUES (1, 'foo');`
	if _, err := db.Exec(insert); err != nil {
		t.Fatalf("Failed to insert data: %v", err)
	}

	// Use a pipe to simulate user input
	r, w := io.Pipe()
	var wg sync.WaitGroup
	wg.Add(1)
	go func() {
		defer wg.Done()
		defer w.Close()
		io.WriteString(w, "SELECT * FROM test;\n")
	}()

	// Capture the output in a buffer
	var outBuf bytes.Buffer
	err = Prompt(context.Background(), db, r, &outBuf)
	if err != nil && err.Error() != "failed to read line: EOF" {
		t.Fatalf("Prompt failed: %v", err)
	}

	wg.Wait()

	// Define the expected output
	expected := `
+----+------+
| ID | NAME |
+----+------+
|  1 | foo  |
+----+------+
`
	// Trim whitespace for a more robust comparison
	got := strings.TrimSpace(outBuf.String())
	want := strings.TrimSpace(expected)

	if !strings.Contains(got, want) {
		t.Errorf("Prompt() got = %v, want %v", got, want)
	}
}

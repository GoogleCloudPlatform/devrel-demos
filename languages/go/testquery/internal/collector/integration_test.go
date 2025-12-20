package collector

import (
	"context"
	"database/sql"
	"os"
	"path/filepath"
	"testing"

	_ "github.com/mattn/go-sqlite3"
)

func setupIntegrationTest(t *testing.T) (string, func()) {
	tmpDir, err := os.MkdirTemp("", "integration-test-")
	if err != nil {
		t.Fatalf("Failed to create temp dir: %v", err)
	}

	// Create a dummy Go project
	goModContent := "module test-project"
	goModPath := filepath.Join(tmpDir, "go.mod")
	if err := os.WriteFile(goModPath, []byte(goModContent), 0644); err != nil {
		t.Fatalf("Failed to write go.mod: %v", err)
	}

	mainContent := `package main

func Add(a, b int) int {
	return a + b
}`
	mainPath := filepath.Join(tmpDir, "main.go")
	if err := os.WriteFile(mainPath, []byte(mainContent), 0644); err != nil {
		t.Fatalf("Failed to write main.go: %v", err)
	}

	mainTestContent := `package main

import "testing"

func TestAdd(t *testing.T) {
	if Add(1, 2) != 3 {
		t.Error("1 + 2 should be 3")
	}
}

func TestFail(t *testing.T) {
	t.Error("this test is designed to fail")
}
`
	mainTestPath := filepath.Join(tmpDir, "main_test.go")
	if err := os.WriteFile(mainTestPath, []byte(mainTestContent), 0644); err != nil {
		t.Fatalf("Failed to write main_test.go: %v", err)
	}

	return tmpDir, func() {
		os.RemoveAll(tmpDir)
	}
}

func TestPopulateTestResults(t *testing.T) {
	tmpDir, cleanup := setupIntegrationTest(t)
	defer cleanup()

	// Change to the temporary directory to run go test
	oldWd, err := os.Getwd()
	if err != nil {
		t.Fatalf("Failed to get current working directory: %v", err)
	}
	if err := os.Chdir(tmpDir); err != nil {
		t.Fatalf("Failed to change directory: %v", err)
	}
	defer os.Chdir(oldWd)

	// Create an in-memory SQLite database
	db, err := sql.Open("sqlite3", ":memory:")
	if err != nil {
		t.Fatalf("Failed to open in-memory database: %v", err)
	}
	defer db.Close()

	// Create the database schema
	schema := `
	CREATE TABLE all_tests (
		"time" TIMESTAMP NOT NULL,
		"action" TEXT NOT NULL,
		package TEXT NOT NULL,
        test TEXT NOT NULL,
        elapsed NUMERIC NULL,
        "output" TEXT NULL
	);`
	if _, err := db.Exec(schema); err != nil {
		t.Fatalf("Failed to create schema: %v", err)
	}

	// Run the function to be tested
	_, err = PopulateTestResults(context.Background(), db, []string{"./..."})
	if err != nil {
		t.Fatalf("PopulateTestResults failed: %v", err)
	}

	// Verify the results
	rows, err := db.Query("SELECT test, action FROM all_tests ORDER BY test")
	if err != nil {
		t.Fatalf("Failed to query database: %v", err)
	}
	defer rows.Close()

	var results [][2]string
	for rows.Next() {
		var test, action string
		if err := rows.Scan(&test, &action); err != nil {
			t.Fatalf("Failed to scan row: %v", err)
		}
		results = append(results, [2]string{test, action})
	}

	expectedResults := [][2]string{
		{"TestAdd", "pass"},
		{"TestFail", "fail"},
	}

	if len(results) != len(expectedResults) {
		t.Fatalf("Expected %d results, but got %d", len(expectedResults), len(results))
	}

	for i, result := range results {
		if result[0] != expectedResults[i][0] || result[1] != expectedResults[i][1] {
			t.Errorf("Expected result %v, but got %v", expectedResults[i], result)
		}
	}
}

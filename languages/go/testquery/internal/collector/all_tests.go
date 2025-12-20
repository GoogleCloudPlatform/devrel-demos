package collector

import (
	"bytes"
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"os/exec"
	"time"
)

// TestResult represents the structure of a test result
type TestEvent struct {
	Time    time.Time `json:"time"`
	Action  string    `json:"action"`
	Package string    `json:"package"`
	Test    string    `json:"test"`
	Elapsed *float64  `json:"elapsed,omitempty"`
	Output  *string   `json:"output,omitempty"`
}

// collectTestResults runs `go test -json` and parses the output
func collectTestResults(pkgDirs []string) ([]TestEvent, error) {
	args := []string{"test"}
	args = append(args, pkgDirs...)
	args = append(args, "-json", "-coverprofile=coverage.out")

	cmd := exec.Command("go", args...)
	cmd.Dir = "." // Run from project root
	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	cmd.Run()

	tests, err := parseTestOutput(stdout.Bytes())
	if err != nil {
		return nil, fmt.Errorf("failed to parse test output: %w. Output: %s", err, stderr.String())
	}

	var results []TestEvent
	for _, test := range tests {
		if test.Test == "" || (test.Action != "pass" && test.Action != "fail") {
			continue
		}
		results = append(results, test)
	}
	return results, nil
}

func parseTestOutput(output []byte) ([]TestEvent, error) {
	var result []TestEvent
	decoder := json.NewDecoder(bytes.NewReader(output))
	for {
		var event TestEvent
		if err := decoder.Decode(&event); err == io.EOF {
			break
		} else if err != nil {
			return nil, err
		}
		result = append(result, event)
	}
	return result, nil
}

func PopulateTestResults(ctx context.Context, db *sql.DB, pkgDirs []string) ([]TestEvent, error) {
	testResults, err := collectTestResults(pkgDirs)
	if err != nil {
		return nil, fmt.Errorf("failed to collect test results: %w", err)
	}

	for _, test := range testResults {

		insertSQL := "INSERT INTO all_tests (\"time\", \"action\", package, test, elapsed, \"output\") VALUES (?, ?, ?, ?, ?, ?);"
		_, err = db.ExecContext(ctx, insertSQL, test.Time, test.Action, test.Package, test.Test, test.Elapsed, test.Output)
		if err != nil {
			return nil, fmt.Errorf("failed to insert test results: %w", err)
		}
	}

	return testResults, nil
}

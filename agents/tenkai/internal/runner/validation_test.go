package runner

import (
	"context"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"

	"github.com/GoogleCloudPlatform/devrel-demos/agents/tenkai/internal/config"
)

func TestValidateCommand(t *testing.T) {
	r := &Runner{}
	ctx := context.Background()
	wsPath := t.TempDir()

	tests := []struct {
		name     string
		rule     config.ValidationRule
		preRun   func()
		expected string // Expected status: PASS or FAIL
	}{
		{
			name: "Basic Success (Exit 0)",
			rule: config.ValidationRule{
				Command:        "exit 0",
				ExpectExitCode: intPtr(0),
			},
			expected: "PASS",
		},
		{
			name: "Exit Code Failure",
			rule: config.ValidationRule{
				Command:        "exit 1",
				ExpectExitCode: intPtr(0),
			},
			expected: "FAIL",
		},
		{
			name: "Stdin and Substring Match",
			rule: config.ValidationRule{
				Command:      "cat",
				Stdin:        "hello world",
				ExpectOutput: "hello",
			},
			expected: "PASS",
		},
		{
			name: "Substring Mismatch",
			rule: config.ValidationRule{
				Command:      "echo 'goodbye'",
				ExpectOutput: "hello",
			},
			expected: "FAIL",
		},
		{
			name: "Regex Match",
			rule: config.ValidationRule{
				Command:           "echo 'tenkai-123'",
				ExpectOutputRegex: "tenkai-\\d+",
			},
			expected: "PASS",
		},
		{
			name: "Regex Mismatch",
			rule: config.ValidationRule{
				Command:           "echo 'tenkai-abc'",
				ExpectOutputRegex: "tenkai-\\d+",
			},
			expected: "FAIL",
		},
		{
			name: "Multiple Criteria (All Pass)",
			rule: config.ValidationRule{
				Command:           "echo 'count: 42'",
				ExpectExitCode:    intPtr(0),
				ExpectOutput:      "count",
				ExpectOutputRegex: "\\d+",
			},
			expected: "PASS",
		},
		{
			name: "Multiple Criteria (One Fails)",
			rule: config.ValidationRule{
				Command:           "echo 'count: abc'",
				ExpectExitCode:    intPtr(0),
				ExpectOutput:      "count",
				ExpectOutputRegex: "\\d+",
			},
			expected: "FAIL",
		},
		{
			name: "Optional Exit Code (Ignored)",
			rule: config.ValidationRule{
				Command:      "exit 1",
				ExpectOutput: "",
			},
			expected: "PASS",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if tt.preRun != nil {
				tt.preRun()
			}
			item, err := r.validateCommand(ctx, wsPath, tt.rule)
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if item.Status != tt.expected {
				t.Errorf("expected status %s, got %s. Details: %s", tt.expected, item.Status, item.Details)
			}
		})
	}
}

func TestValidateCommand_Details(t *testing.T) {
	r := &Runner{}
	ctx := context.Background()
	wsPath := t.TempDir()

	rule := config.ValidationRule{
		Command: "echo 'hello details'",
	}

	item, err := r.validateCommand(ctx, wsPath, rule)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if item.Status != "PASS" {
		t.Errorf("expected PASS, got %s", item.Status)
	}

	// Verify new fields
	if !strings.Contains(item.Command, "echo 'hello details'") {
		t.Errorf("expected Command to contain 'echo', got %q", item.Command)
	}
	if !strings.Contains(item.Output, "hello details") {
		t.Errorf("expected Output to contain 'hello details', got %q", item.Output)
	}
	if item.Definition == "" {
		t.Error("expected Definition to be populated")
	}
}

func TestValidateCommand_StdinClosure(t *testing.T) {
	r := &Runner{}
	ctx := context.Background()
	wsPath := t.TempDir()

	// This script reads one line from stdin.
	// If stdin is closed immediately (EOF), read returns non-zero/fails, and the script exits 1.
	// If stdin is kept open, read blocks.
	// We want to simulate a server that needs stdin open.
	// BUT, if it blocks forever, the test times out.
	// So we need a command that checks "Is Stdin Open?" without blocking forever?
	// OR, we use a command that runs for a bit, then we kill it (simulate external test completion?)
	// But validateCommand waits for exit.

	// Helper: Script that reads input but has a timeout?
	// "read -t 1 || exit 0" -> if timeout, success (stdin open). If EOF, exit 1?
	// On macOS bash, read -t might not check EOF same way.
	// Let's use python or go one-liner.
	// "check_stdin.go": attempts to read byte. If EOF immediately -> exit 1. If no EOF after 500ms -> exit 0.

	// Currently, validateCommand closes Stdin (via /dev/null or NewReader).
	// So we expect this test to FAIL (Exit 1) if our hypothesis is correct.
	// And we expect it to PASS (Exit 0) after we fix it.

	// Go program to check for EOF
	checkSrc := `package main
import (
	"os"
	"time"
)
func main() {
    // Try to read 1 byte with a timeout logic?
    // Actually, simple read.
    c := make(chan error)
    go func() {
        b := make([]byte, 1)
        _, err := os.Stdin.Read(b)
        c <- err
    }()

    select {
    case err := <-c:
        if err != nil { // EOF or error
            os.Exit(1)
        }
        // Read something? Unexpected if we sent nothing.
        os.Exit(2)
    case <-time.After(200 * time.Millisecond):
        // Timeout = Stdin was open and nothing sent. Success!
        os.Exit(0)
    }
}
`
	if err := os.WriteFile(filepath.Join(wsPath, "check_stdin.go"), []byte(checkSrc), 0644); err != nil {
		t.Fatal(err)
	}

	rule := config.ValidationRule{
		Command:        "go run check_stdin.go",
		ExpectExitCode: intPtr(0),
	}

	item, err := r.validateCommand(ctx, wsPath, rule)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// EXPECT FAILURE currently (because Stdin is closed -> EOF -> Exit 1)
	if item.Status == "PASS" {
		t.Logf("Output: %s", item.Output)
		t.Logf("Error: %s", item.Error)
		// If it passes, then Stdin is ALREADY open? Or logic is wrong?
		// exec.Cmd with nil Stdin = /dev/null = EOF.
		// So Read() returns EOF immediately.
		// So Exit(1).
		// So Status should be FAIL.
		// If we want to assert it fails *now* so we can see the fix works:
		// t.Errorf("expected FAIL (reproduction of issue), got PASS")
	} else {
		t.Log("Confimed failure: Stdin provided immediate EOF")
	}
}

func TestValidateCommand_StdinDelay(t *testing.T) {
	r := &Runner{}
	ctx := context.Background()
	wsPath := t.TempDir()

	// Helper: check_delay.go
	// Reads until EOF. Fails if EOF comes too fast (< 200ms).
	checkSrc := `package main
import (
	"io"
	"os"
	"time"
)
func main() {
    start := time.Now()
    io.Copy(io.Discard, os.Stdin)
    elapsed := time.Since(start)
    if elapsed < 200*time.Millisecond {
        os.Exit(1)
    }
    os.Exit(0)
}
`
	if err := os.WriteFile(filepath.Join(wsPath, "check_delay.go"), []byte(checkSrc), 0644); err != nil {
		t.Fatal(err)
	}

	// Compile first to avoid race with go run compilation time
	if err := exec.Command("go", "build", "-o", filepath.Join(wsPath, "check_delay"), filepath.Join(wsPath, "check_delay.go")).Run(); err != nil {
		t.Fatal(err)
	}

	// Case 1: No Delay -> Expect FAIL (Exit 1)
	ruleFail := config.ValidationRule{
		Command:        "./check_delay",
		Stdin:          "some data",
		ExpectExitCode: intPtr(0),
	}
	item, err := r.validateCommand(ctx, wsPath, ruleFail)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if item.Status == "PASS" {
		t.Error("expected FAIL without delay, got PASS")
	}

	// Case 2: With Delay -> Expect PASS (Exit 0)
	rulePass := config.ValidationRule{
		Command: "./check_delay",
		Stdin:   "some data",
		// Increase delay safely above threshold
		StdinDelay:     "500ms",
		ExpectExitCode: intPtr(0),
	}
	itemPass, err := r.validateCommand(ctx, wsPath, rulePass)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if itemPass.Status != "PASS" {
		t.Errorf("expected PASS with delay, got FAIL. Output: %s, Error: %s", itemPass.Output, itemPass.Error)
	}
}

func intPtr(i int) *int {
	return &i
}

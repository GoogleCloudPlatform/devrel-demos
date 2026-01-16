package run

import (
	"context"
	"os"
	"strings"
	"testing"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func TestValidateCommand(t *testing.T) {
	tests := []struct {
		name    string
		cmd     string
		args    []string
		force   bool
		wantErr bool
	}{
		{"Allowed: go", "go", []string{"version"}, false, false},
		{"Allowed: python", "python", []string{"script.py"}, false, false},
		{"Allowed: Local Binary", "./bin/server", []string{}, false, false},
		{"Allowed: File Op", "rm", []string{"foo.txt"}, false, false},
		{"Blocked: git", "git", []string{"status"}, false, true},
		{"Blocked: bash", "bash", []string{"-c", "echo hello"}, false, true},
		// Hardened Validation Tests
		{"Universal: Abs Path", "python", []string{"/etc/passwd"}, false, true},
		{"Universal: Traversal", "python", []string{"../header.h"}, false, true},
		{"Universal: Unsafe Flag", "ls", []string{"--config=/etc/config"}, false, true},
		{"Universal: Safe Flag", "ls", []string{"--verbose"}, true, false},
		{"Blocked: File Op Abs Path", "rm", []string{"/etc/passwd"}, false, true},
		{"Blocked: File Op Traversal", "rm", []string{"../foo.txt"}, false, true},
		{"Nudged: grep (no force)", "grep", []string{"func"}, false, true},
		{"Nudged: grep (force)", "grep", []string{"func"}, true, false},
		{"Advisory: go build (no force)", "go", []string{"build", "."}, false, true},
		{"Advisory: go build (force)", "go", []string{"build", "."}, true, false},
		{"Advisory: go mod (no force)", "go", []string{"mod", "tidy"}, false, true},
		{"Advisory: go get (force)", "go", []string{"get", "example.com/pkg"}, true, false},
		{"Metacharacter", "ls", []string{";", "rm", "-rf", "/"}, false, true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := validateCommand(tt.cmd, tt.args, tt.force)
			if (err != nil) != tt.wantErr {
				t.Errorf("validateCommand() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

func TestHandler_OutputTruncation(t *testing.T) {
	// Create a dummy script that prints a lot of data
	script := "print('a' * 20000)"
	err := os.WriteFile("test_spew.py", []byte(script), 0644)
	if err != nil {
		t.Skip("skipping test, cannot write test script")
	}
	defer os.Remove("test_spew.py")

	params := Params{
		Command: "python3",
		Args:    []string{"-c", script},
	}

	res, _, err := Handler(context.Background(), &mcp.CallToolRequest{}, params)
	if err != nil {
		t.Fatalf("Handler failed: %v", err)
	}

	content := res.Content[0].(*mcp.TextContent).Text
	if !strings.Contains(content, "WARNING: Output truncated") {
		t.Errorf("Expected truncation warning, got: %s", content[:100])
	}
	if !strings.Contains(content, "[...HEAD...]") {
		t.Error("Expected head marker")
	}
	if !strings.Contains(content, "[...TAIL...]") {
		t.Error("Expected tail marker")
	}

	// Clean up generated log file
	// We can't easily guess the filename here without parsing the output,
	// but the test is mainly about the response format.
	// In a real integration test we'd check the file existence.
}

func TestHandler_Input(t *testing.T) {
	params := Params{
		Command: "python3",
		Args:    []string{"-c", "import sys; print(sys.stdin.read().strip().upper())"},
		Input:   "hello world",
	}

	res, _, err := Handler(context.Background(), &mcp.CallToolRequest{}, params)
	if err != nil {
		t.Fatalf("Handler failed: %v", err)
	}

	content := res.Content[0].(*mcp.TextContent).Text
	if !strings.Contains(content, "HELLO WORLD") {
		t.Errorf("Expected 'HELLO WORLD', got: %q", content)
	}
}

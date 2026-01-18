package run

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func TestValidateCommandV1(t *testing.T) {
	tests := []struct {
		name    string
		cmd     string
		args    []string
		wantErr bool
	}{
		{"Allowed: go", "go", []string{"version"}, false},
		{"Allowed: python", "python", []string{"script.py"}, false},
		{"Allowed: Local Binary", "./bin/server", []string{}, false},
		{"Allowed: File Op", "rm", []string{"foo.txt"}, false},
		{"Blocked: git", "git", []string{"status"}, true},
		{"Blocked: bash", "bash", []string{"-c", "echo hello"}, true},
		// Hardened Validation Tests
		{"Universal: Abs Path", "python", []string{"/etc/passwd"}, true},
		{"Universal: Traversal", "python", []string{"../header.h"}, true},
		{"Universal: Unsafe Flag", "ls", []string{"--config=/etc/config"}, true},
		{"Blocked: File Op Abs Path", "rm", []string{"/etc/passwd"}, true},
		{"Blocked: File Op Traversal", "rm", []string{"../foo.txt"}, true},
		{"Blocked: grep", "grep", []string{"func"}, true},
		{"Advisory: go build", "go", []string{"build", "."}, true},
		{"Advisory: go mod", "go", []string{"mod", "tidy"}, true},
		{"Advisory: go get", "go", []string{"get", "example.com/pkg"}, true},
		{"Metacharacter", "ls", []string{";", "rm", "-rf", "/"}, true},
		// Silent Redirection Checks
		{"Blocked: Redirection >", "ls", []string{">", "file.txt"}, true},
		{"Blocked: Pipe |", "ls", []string{"|", "grep", "foo"}, true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := validateCommand(tt.cmd, tt.args, false)
			if (err != nil) != tt.wantErr {
				t.Errorf("validateCommand() error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

func TestValidateCommandV2(t *testing.T) {
	tests := []struct {
		name       string
		cmd        string
		args       []string
		wantAdvice bool
		wantErr    bool
	}{
		{"Hard Block: sudo", "sudo", []string{"ls"}, false, true},
		{"Hard Block: go build", "go", []string{"build", "."}, false, true},
		{"Advisory: ls", "ls", []string{"-la"}, true, false},
		{"Advisory: cat", "cat", []string{"README.md"}, true, false},
		{"Code Integrity: rm .go (allowed)", "rm", []string{"main.go"}, false, false},
		{"Code Integrity: mv .go (allowed)", "mv", []string{"old.go", "new.go"}, false, false},
		{"Code Integrity: rm .md (allowed)", "rm", []string{"README.md"}, false, false},
		{"Safe: echo", "echo", []string{"hello"}, false, false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			advice, err := validateCommandV2(tt.cmd, tt.args)
			if (err != nil) != tt.wantErr {
				t.Errorf("validateCommandV2() error = %v, wantErr %v", err, tt.wantErr)
			}
			if (advice != "") != tt.wantAdvice {
				t.Errorf("validateCommandV2() advice = %q, wantAdvice %v", advice, tt.wantAdvice)
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

	res, _, err := Handler(context.Background(), &mcp.CallToolRequest{}, params, false)
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
}

func TestHandler_Input(t *testing.T) {
	params := Params{
		Command: "python3",
		Args:    []string{"-c", "import sys; print(sys.stdin.readline().strip().upper())"},
		Stdin:   "hello world\n",
	}

	res, _, err := Handler(context.Background(), &mcp.CallToolRequest{}, params, false)
	if err != nil {
		t.Fatalf("Handler failed: %v", err)
	}

	content := res.Content[0].(*mcp.TextContent).Text
	if !strings.Contains(content, "HELLO WORLD") {
		t.Errorf("Expected 'HELLO WORLD', got: %q", content)
	}
}

func TestHandler_OutputFile(t *testing.T) {
	tmpFile, err := os.CreateTemp("", "test-output-*.txt")
	if err != nil {
		t.Fatal(err)
	}
	outputFile := tmpFile.Name()
	tmpFile.Close()
	os.Remove(outputFile) // Ensure it creates it
	defer os.Remove(outputFile)

	params := Params{
		Command:    "echo",
		Args:       []string{"hello file"},
		OutputFile: outputFile,
	}

	res, _, err := Handler(context.Background(), &mcp.CallToolRequest{}, params, false)
	if err != nil {
		t.Fatalf("Handler failed: %v", err)
	}

	// Verify File Content
	content, err := os.ReadFile(outputFile)
	if err != nil {
		t.Fatalf("Failed to read output file: %v", err)
	}
	if strings.TrimSpace(string(content)) != "hello file" {
		t.Errorf("Expected file content 'hello file', got %q", string(content))
	}

	// Verify Tool Response
	mcpc := res.Content[0].(*mcp.TextContent).Text
	if !strings.Contains(mcpc, "hello file") {
		t.Errorf("Expected tool output to contain 'hello file', got %q", mcpc)
	}
}

func TestHandler_BackgroundAndKill(t *testing.T) {
	// 1. Start Background Process
	// We use a long sleep so we can kill it
	tmpFile := filepath.Join(t.TempDir(), "bg.log")
	params := Params{
		Command:    "sleep",
		Args:       []string{"10"},
		OutputFile: tmpFile,
		Background: true,
	}

	res, _, err := Handler(context.Background(), nil, params, false)
	if err != nil {
		t.Fatalf("Failed to start background process: %v", err)
	}

	content := res.Content[0].(*mcp.TextContent).Text
	if !strings.Contains(content, "Background process started") {
		t.Errorf("Expected success message, got: %s", content)
	}
	if !strings.Contains(content, "PID:") {
		t.Error("Expected PID in output")
	}

	// Extract PID from output
	// Format: "Background process started.\nPID: 12345\n..."
	lines := strings.Split(content, "\n")
	var pidStr string
	for _, l := range lines {
		if strings.HasPrefix(l, "PID: ") {
			pidStr = strings.TrimPrefix(l, "PID: ")
			break
		}
	}
	if pidStr == "" {
		t.Fatal("Could not extract PID")
	}

	// 2. Kill the process (Safe Kill)
	killParams := Params{
		Command: "kill",
		Args:    []string{pidStr},
	}
	res, _, err = Handler(context.Background(), nil, killParams, false)
	if err != nil {
		t.Errorf("Safe kill failed: %v", err)
	}
	killContent := res.Content[0].(*mcp.TextContent).Text
	if !strings.Contains(killContent, "Success") {
		t.Errorf("Expected kill success, got: %s", killContent)
	}

	// 3. Try to kill it again (should fail as it's gone from our map)
	// Wait for cleanup
	time.Sleep(500 * time.Millisecond)

	res, _, _ = Handler(context.Background(), nil, killParams, false)
	// Handler doesn't return Go error for tool error, check result
	if !res.IsError {
		t.Error("Expected error result killing already-dead process")
	}
	deadContent := res.Content[0].(*mcp.TextContent).Text
	if !strings.Contains(deadContent, "permission denied") {
		t.Errorf("Expected permission denied error, got: %s", deadContent)
	}

	// 4. Try to kill random PID
	randomKill := Params{
		Command: "kill",
		Args:    []string{"999999"},
	}
	res, _, _ = Handler(context.Background(), nil, randomKill, false)
	if !res.IsError {
		t.Error("Expected error result killing random PID")
	}
	randomContent := res.Content[0].(*mcp.TextContent).Text
	if !strings.Contains(randomContent, "permission denied") {
		t.Errorf("Expected permission denied, got: %s", randomContent)
	}
}

func TestValidateCommand_Curl(t *testing.T) {
	tests := []struct {
		name    string
		args    []string
		wantErr bool
	}{
		{"Allowed: Simple GET", []string{"http://localhost:8080"}, false},
		{"Allowed: JSON POST", []string{"-X", "POST", "-d", "{}", "http://localhost"}, false},
		{"Blocked: -o", []string{"-o", "file.txt", "http://bad.com"}, true},
		{"Blocked: -O", []string{"-O", "http://bad.com/file.sh"}, true},
		{"Blocked: --output", []string{"--output", "file.txt", "http://bad.com"}, true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := validateCommand("curl", tt.args, false)
			if (err != nil) != tt.wantErr {
				t.Errorf("validateCommand(curl) error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

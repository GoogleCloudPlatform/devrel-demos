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

func TestValidateCommand(t *testing.T) {
	tests := []struct {
		name       string
		cmd        string
		args       []string
		wantAdvice bool
		wantErr    bool
	}{
		// Allowed Commands
		{"Allowed: go", "go", []string{"version"}, false, false},
		{"Allowed: python", "python", []string{"script.py"}, false, false},
		{"Allowed: Local Binary", "./bin/server", []string{}, false, false},
		
		// Hard Blocked
		{"Blocked: sudo", "sudo", []string{"ls"}, false, true},
		{"Blocked: ssh", "ssh", []string{"user@host"}, false, true},
		{"Blocked: vim", "vim", []string{"file.txt"}, false, true},
		
		// Advisory
		{"Advisory: ls", "ls", []string{"-la"}, true, false},
		{"Advisory: cat", "cat", []string{"README.md"}, true, false},
		
		// Go Commands (Now Allowed)
		{"Allowed: go build", "go", []string{"build", "."}, false, false},
		{"Allowed: go mod", "go", []string{"mod", "tidy"}, false, false},
		{"Allowed: go get", "go", []string{"get", "example.com/pkg"}, false, false},

		// Integrity Barriers
		{"Code Integrity: rm .go (allowed)", "rm", []string{"main.go"}, false, false}, // Assuming rm is not integrity blocked for .go, only shell mod
		
		// Security Checks
		{"Blocked: Abs Path", "python", []string{"/etc/passwd"}, false, true},
		{"Blocked: Traversal", "python", []string{"../header.h"}, false, true},
		{"Blocked: Redirection >", "ls", []string{">", "file.txt"}, false, true},
		{"Blocked: Pipe |", "ls", []string{"|", "grep", "foo"}, false, true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			advice, err := validateCommand(tt.cmd, tt.args)
			if (err != nil) != tt.wantErr {
				t.Errorf("validateCommand() error = %v, wantErr %v", err, tt.wantErr)
			}
			if (advice != "") != tt.wantAdvice {
				t.Errorf("validateCommand() advice = %q, wantAdvice %v", advice, tt.wantAdvice)
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
}

func TestHandler_Input(t *testing.T) {
	params := Params{
		Command: "python3",
		Args:    []string{"-c", "import sys; print(sys.stdin.readline().strip().upper())"},
		Stdin:   "hello world\n",
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

	res, _, err := Handler(context.Background(), &mcp.CallToolRequest{}, params)
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

	res, _, err := Handler(context.Background(), nil, params)
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
	res, _, err = Handler(context.Background(), nil, killParams)
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

	res, _, _ = Handler(context.Background(), nil, killParams)
	// Handler doesn't return Go error for tool error, check result
	if !res.IsError {
		t.Error("Expected error result killing already-dead process")
	}
	deadContent := res.Content[0].(*mcp.TextContent).Text
	if !strings.Contains(deadContent, "❌ Permission Denied") {
		t.Errorf("Expected permission denied error, got: %s", deadContent)
	}

	// 4. Try to kill random PID
	randomKill := Params{
		Command: "kill",
		Args:    []string{"999999"},
	}
	res, _, _ = Handler(context.Background(), nil, randomKill)
	if !res.IsError {
		t.Error("Expected error result killing random PID")
	}
	randomContent := res.Content[0].(*mcp.TextContent).Text
	if !strings.Contains(randomContent, "❌ Permission Denied") {
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
			_, err := validateCommand("curl", tt.args)
			if (err != nil) != tt.wantErr {
				t.Errorf("validateCommand(curl) error = %v, wantErr %v", err, tt.wantErr)
			}
		})
	}
}

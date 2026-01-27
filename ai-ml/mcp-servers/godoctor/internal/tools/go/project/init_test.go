package project

import (
        "context"
        "fmt"
        "os"
        "path/filepath"
        "strings"
        "testing"

        "github.com/modelcontextprotocol/go-sdk/mcp"
)

type mockRunner struct {
        commands []string
        outputs  map[string]string
        errors   map[string]error
}

func (r *mockRunner) Run(ctx context.Context, dir, name string, args ...string) (string, error) {
        cmd := name + " " + strings.Join(args, " ")
        r.commands = append(r.commands, cmd)

        // Check for errors first
        for k, v := range r.errors {
                if strings.Contains(cmd, k) {
                        return "", v
                }
        }

        // Check for outputs
        for k, v := range r.outputs {
                if strings.Contains(cmd, k) {
                        return v, nil
                }
        }

        return "", nil
}

func TestProjectInit(t *testing.T) {
        // Setup temporary directory
        tmpDir := t.TempDir()
        targetDir := filepath.Join(tmpDir, "newproject")

        // Mock Runner
        oldRunner := CommandRunner
        defer func() { CommandRunner = oldRunner }()

        mock := &mockRunner{
                outputs: map[string]string{
                        "go mod init": "go: creating new go.mod: module example.com/test",
                        "go get github.com/user/valid": "go: downloading github.com/user/valid v1.0.0",
                },
                errors: map[string]error{
                        "go get github.com/user/invalid": fmt.Errorf("exit status 1"),
                },
        }
        CommandRunner = mock

        // Test Params
        params := Params{
                Path:       targetDir,
                ModulePath: "example.com/test",
                Dependencies: []string{
                        "github.com/user/valid",
                        "github.com/user/invalid",
                },
        }

        // Run Handler
        res, _, err := Handler(context.Background(), nil, params)
        if err != nil {
                t.Fatalf("Handler failed: %v", err)
        }

        if res.IsError {
                t.Errorf("Expected success, got error result: %v", res.Content)
        }

        output := res.Content[0].(*mcp.TextContent).Text

        // Verify Directory Creation
        if _, err := os.Stat(targetDir); os.IsNotExist(err) {
                t.Errorf("Target directory not created")
        }

        // Verify go.mod check logic (we can't easily check go.mod content since we mocked the command, 
        // but the handler checks for existence before running. wait, the handler creates the dir, 
        // but 'go mod init' command is what creates go.mod usually. 
        // Since we mocked 'go mod init', no go.mod file is actually created by the command on disk.
        // But the Handler doesn't check for go.mod existence *after* running command, only before.

        // Verify Output strings
        expectedStrings := []string{
                "Successfully initialized Go project",
                "Module: `example.com/test`",
                "✅ `github.com/user/valid` installed",
                "⚠️ Failed to get `github.com/user/invalid`",
        }

        for _, s := range expectedStrings {
                if !strings.Contains(output, s) {
                        t.Errorf("Expected output to contain %q, got:\n%s", s, output)
                }
        }

        // Verify Commands Executed
        expectedCmds := []string{
                "go mod init example.com/test",
                "go get github.com/user/valid",
                "go get github.com/user/invalid",
                "go mod tidy",
        }

        for _, s := range expectedCmds {
                found := false
                for _, cmd := range mock.commands {
                        if strings.Contains(cmd, s) {
                                found = true
                                break
                        }
                }
                if !found {
                        t.Errorf("Expected command %q to be executed", s)
                }
        }

        // Verify NO main.go creation
        mainPath := filepath.Join(targetDir, "main.go")
        if _, err := os.Stat(mainPath); !os.IsNotExist(err) {
                t.Errorf("Expected main.go NOT to exist, but it does")
        }
}

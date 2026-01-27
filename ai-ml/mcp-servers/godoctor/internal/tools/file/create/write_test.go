package create

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func TestWrite(t *testing.T) {
	tmpDir, err := os.MkdirTemp("", "write-test-*")
	if err != nil {
		t.Fatal(err)
	}
	//nolint:errcheck
	defer os.RemoveAll(tmpDir)

	if err := os.WriteFile(filepath.Join(tmpDir, "go.mod"), []byte("module write-test\n\ngo 1.24\n"), 0644); err != nil {
		t.Fatal(err)
	}

	filePath := filepath.Join(tmpDir, "lib.go")

	// 1. Overwrite (Initial create)
	res, _, _ := toolHandler(context.TODO(), nil, Params{
		Filename: filePath,
		Content:  "package lib\n\nfunc A() {}",
	})
	if res.IsError {
		t.Fatalf("Initial write failed: %v", res.Content[0].(*mcp.TextContent).Text)
	}

	//nolint:gosec // G304: Test file path.
	content, _ := os.ReadFile(filePath)
	if !strings.Contains(string(content), "func A()") {
		t.Errorf("expected func A() in file, got: %s", string(content))
	}
}

func TestWrite_Validation(t *testing.T) {
	tmpDir, err := os.MkdirTemp("", "write-val-*")
	if err != nil {
		t.Fatal(err)
	}
	//nolint:errcheck
	defer os.RemoveAll(tmpDir)
	if err := os.WriteFile(filepath.Join(tmpDir, "go.mod"), []byte("module val-test\n\ngo 1.24\n"), 0644); err != nil {
		t.Fatal(err)
	}

	filePath := filepath.Join(tmpDir, "main.go")

	// Write code with missing import/symbol
	res, _, _ := toolHandler(context.TODO(), nil, Params{
		Filename: filePath,
		Content:  "package main\n\nfunc main() { fmt.Println(NonExistent) }",
	})

	output := res.Content[0].(*mcp.TextContent).Text
	// imports.Process should have added "fmt"
	// and parser.ParseFile should report success (syntax is ok, but type is not)
	// Wait, fmt.Println(NonExistent) is VALID syntax.
	if strings.Contains(output, "WARNING") {
		t.Errorf("unexpected warning for valid syntax: %s", output)
	}

	// Now try invalid syntax
	// imports.Process will catch this first!
	resErr, _, _ := toolHandler(context.TODO(), nil, Params{
		Filename: filePath,
		Content:  "package main\n\nfunc main() { this is invalid syntax }",
	})
	outputErr := resErr.Content[0].(*mcp.TextContent).Text
	// It returns errorResult, so it should be in the text content but marked as IsError.
	if !strings.Contains(outputErr, "write produced invalid Go code") {
		t.Errorf("expected syntax check warning, got: %s", outputErr)
	}
}

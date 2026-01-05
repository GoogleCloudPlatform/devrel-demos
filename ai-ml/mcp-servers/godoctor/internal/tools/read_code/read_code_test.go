package read_code

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func TestReadCodeTool(t *testing.T) {
	// Create temp dir with module setup to allow analysis
	tmpDir := t.TempDir()

	// Create go.mod
	if err := os.WriteFile(filepath.Join(tmpDir, "go.mod"), []byte("module example.com/test\ngo 1.21\n"), 0644); err != nil {
		t.Fatal(err)
	}

	srcFile := filepath.Join(tmpDir, "main.go")
	src := `package main

import "fmt"

type MyStruct struct {
	Name string
}

func (s *MyStruct) Greet() string {
	return "Hello " + s.Name
}

func main() {
	fmt.Println("Hello")
	undefinedFunc() // This should trigger an analysis error
}
`
	if err := os.WriteFile(srcFile, []byte(src), 0644); err != nil {
		t.Fatal(err)
	}

	// Call tool
	res, _, err := readCodeHandler(context.Background(), nil, Params{FilePath: srcFile})
	if err != nil {
		t.Fatalf("handler failed: %v", err)
	}

	if res.IsError {
		t.Errorf("tool returned error: %v", res.Content)
	}

	if len(res.Content) == 0 {
		t.Fatal("no content returned")
	}

	textContent, ok := res.Content[0].(*mcp.TextContent)
	if !ok {
		t.Fatal("content is not text")
	}
	text := textContent.Text

	// Check for symbols
	if !strings.Contains(text, "| `MyStruct` | Type | 5 |") {
		t.Errorf("expected MyStruct type in table, got: %s", text)
	}
	if !strings.Contains(text, "| `(*MyStruct) Greet` | Function | 9 |") {
		t.Errorf("expected Greet method in table, got: %s", text)
	}
	if !strings.Contains(text, "| `main` | Function | 13 |") {
		t.Errorf("expected main function in table, got: %s", text)
	}

	// Check for Analysis
	if !strings.Contains(text, "## Analysis (Problems)") {
		t.Errorf("expected Analysis section, got: %s", text)
	}
	if !strings.Contains(text, "undefined: undefinedFunc") {
		t.Errorf("expected undefinedFunc error in analysis, got: %s", text)
	}

	// Check for content
	if !strings.Contains(text, "package main") {
		t.Errorf("expected file content, got: %s", text)
	}
}

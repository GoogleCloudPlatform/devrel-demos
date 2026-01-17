package read

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
	//nolint:gosec // G306: Test permissions.
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
	//nolint:gosec // G306: Test permissions.
	if err := os.WriteFile(srcFile, []byte(src), 0644); err != nil {
		t.Fatal(err)
	}

	// Call tool
	res, _, err := readCodeHandler(context.Background(), nil, Params{Filename: srcFile})
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

	// Check for line numbers
	if !strings.Contains(text, "   1 | package main") {
		t.Errorf("expected line numbers (e.g. '   1 | package main'), got: %s", text)
	}

	// Check that Symbols are GONE
	if strings.Contains(text, "## Symbols") {
		t.Error("Output should NOT contain ## Symbols section anymore")
	}

	// Check for Analysis
	if !strings.Contains(text, "## Analysis (Problems)") {
		t.Errorf("expected Analysis section, got: %s", text)
	}
	if !strings.Contains(text, "undefined: undefinedFunc") {
		t.Errorf("expected undefinedFunc error in analysis, got: %s", text)
	}

	// Check for Referenced Symbols
	// Note: We used "fmt" in the test code, so it should appear
	if !strings.Contains(text, "## Referenced Symbols") {
		t.Errorf("expected Referenced Symbols section, got: %s", text)
	}
	if !strings.Contains(text, "- `fmt.Println`") {
		t.Errorf("expected fmt.Println in dependencies, got: %s", text)
	}
}

func TestReadCodeTool_Partial(t *testing.T) {
	// Create temp dir
	tmpDir := t.TempDir()
	srcFile := filepath.Join(tmpDir, "partial.go")
	src := `line 1
line 2
line 3
line 4
line 5`
	if err := os.WriteFile(srcFile, []byte(src), 0644); err != nil {
		t.Fatal(err)
	}

	// Test case: Read lines 2-4
	res, _, err := readCodeHandler(context.Background(), nil, Params{
		Filename:  srcFile,
		StartLine: 2,
		EndLine:   4,
	})
	if err != nil {
		t.Fatalf("handler failed: %v", err)
	}

	text := res.Content[0].(*mcp.TextContent).Text

	// Should contain lines 2, 3, 4
	if !strings.Contains(text, "   2 | line 2") {
		t.Errorf("expected line 2, got: %s", text)
	}
	if !strings.Contains(text, "   4 | line 4") {
		t.Errorf("expected line 4, got: %s", text)
	}
	// Should NOT contain line 1 or 5
	if strings.Contains(text, "   1 | line 1") {
		t.Errorf("did not expect line 1, got: %s", text)
	}
	if strings.Contains(text, "   5 | line 5") {
		t.Errorf("did not expect line 5, got: %s", text)
	}

	// Should contain "Partial read - analysis skipped"
	if !strings.Contains(text, "Partial read - analysis skipped") {
		t.Error("expected partial read warning")
	}
}

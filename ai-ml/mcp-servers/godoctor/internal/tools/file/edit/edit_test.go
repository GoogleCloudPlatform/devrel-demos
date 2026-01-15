package edit

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/danicat/godoctor/internal/graph"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func TestEdit(t *testing.T) {
	tmpDir, err := os.MkdirTemp("", "edit-test-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	os.WriteFile(filepath.Join(tmpDir, "go.mod"), []byte("module test\n\ngo 1.24\n"), 0644)

	content := `package main
import "fmt"

func main() {
	fmt.Println("Hello")
}
`
	filePath := filepath.Join(tmpDir, "main.go")
	os.WriteFile(filePath, []byte(content), 0644)

	graph.Global = graph.NewManager()

	tests := []struct {
		name     string
		search   string
		replace  string
		expected string
	}{
		{
			"Simple Replace",
			"fmt.Println(\"Hello\")",
			"fmt.Println(\"Goodbye\")",
			"fmt.Println(\"Goodbye\")",
		},
		{
			"Whitespace Agnostic",
			"func main() {\n\tfmt.Println(\"Goodbye\")\n}",
			"func main() { fmt.Println(\"Modified\") }",
			"fmt.Println(\"Modified\")",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			res, _, err := toolHandler(context.TODO(), nil, Params{
				File:          filePath,
				SearchContext: tt.search,
				Replacement:   tt.replace,
			})
			if err != nil {
				t.Fatalf("toolHandler failed: %v", err)
			}
			if res.IsError {
				t.Fatalf("Tool returned error: %v", res.Content[0].(*mcp.TextContent).Text)
			}

			newContent, _ := os.ReadFile(filePath)
			if !strings.Contains(string(newContent), tt.expected) {
				t.Errorf("expected %q in content, got: %s", tt.expected, string(newContent))
			}
		})
	}
}

func TestEdit_Broken(t *testing.T) {
	tmpDir, err := os.MkdirTemp("", "edit-broken-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)
	os.WriteFile(filepath.Join(tmpDir, "go.mod"), []byte("module broken\n\ngo 1.24\n"), 0644)

	filePath := filepath.Join(tmpDir, "main.go")
	os.WriteFile(filePath, []byte("package main\n\nfunc main() {}"), 0644)

	// Introduce a build error
	res, _, _ := toolHandler(context.TODO(), nil, Params{
		File:          filePath,
		SearchContext: "func main() {}",
		Replacement:   "func main() { undefinedVar() }",
	})

	output := res.Content[0].(*mcp.TextContent).Text
	if !strings.Contains(output, "**WARNING:**") || !strings.Contains(output, "undefined") {
		t.Errorf("expected warning about undefinedVar, got: %s", output)
	}
}

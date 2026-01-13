package describe

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/danicat/godoctor/internal/graph"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func TestDescribe_Local(t *testing.T) {
	tmpDir, err := os.MkdirTemp("", "describe-test-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	// Setup module
	os.WriteFile(filepath.Join(tmpDir, "go.mod"), []byte("module testpkg\n\ngo 1.24\n"), 0644)

	content := `package testpkg
import "fmt"

// Message is a constant.
const Message = "Hello"

// User is a struct.
type User struct { Name string }

// SayHello prints hello.
func (u *User) SayHello() {
	fmt.Println(Message)
}

func NewUser(name string) *User {
	return &User{Name: name}
}
`
	filePath := filepath.Join(tmpDir, "test.go")
	os.WriteFile(filePath, []byte(content), 0644)

	// Reset graph for clean test
	graph.Global = graph.NewManager()

	tests := []struct {
		name     string
		symbol   string
		contains []string
	}{
		{"Describe Const", "Message", []string{"const Message = \"Hello\"", "Implementation"}},
		{"Describe Type", "User", []string{"type User struct", "Name string"}},
		{"Describe Method", "User.SayHello", []string{"func (u *User) SayHello()", "fmt.Println(Message)", "type User struct"}},
		{"Describe Func Return", "NewUser", []string{"func NewUser(name string) *User", "type User struct"}},
		{"Describe File", "", []string{"# File:", "package testpkg", "func (u *User) SayHello()"}},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			ctx := context.Background()
			res, _, err := toolHandler(ctx, nil, Params{File: filePath, Symbol: tt.symbol})
			if err != nil {
				t.Fatalf("toolHandler failed: %v", err)
			}
			if res.IsError {
				t.Fatalf("toolHandler returned error: %v", res.Content[0].(*mcp.TextContent).Text)
			}

			output := res.Content[0].(*mcp.TextContent).Text
			for _, c := range tt.contains {
				if !strings.Contains(output, c) {
					t.Errorf("output missing %q: %s", c, output)
				}
			}
		})
	}
}

func TestDescribe_External(t *testing.T) {
	ctx := context.Background()
	res, _, err := toolHandler(ctx, nil, Params{Package: "fmt", Symbol: "Println"})
	if err != nil {
		t.Fatal(err)
	}
	if res.IsError {
		t.Fatal(res.Content[0].(*mcp.TextContent).Text)
	}
	output := res.Content[0].(*mcp.TextContent).Text

	// Updated expectations for Source-Aware Describe
	if !strings.Contains(output, "# Symbol: Println") {
		t.Errorf("missing symbol header: %s", output)
	}
	if !strings.Contains(output, "## Implementation") {
		t.Errorf("missing implementation: %s", output)
	}
	if !strings.Contains(output, "func Println(a ...any)") {
		t.Errorf("missing function signature: %s", output)
	}
}

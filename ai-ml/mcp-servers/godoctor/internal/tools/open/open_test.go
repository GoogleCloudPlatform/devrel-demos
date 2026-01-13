package open

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func TestOpen_Complex(t *testing.T) {
	tmpDir, err := os.MkdirTemp("", "open-complex-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	// Setup module
	os.WriteFile(filepath.Join(tmpDir, "go.mod"), []byte("module complex\n\ngo 1.24\n"), 0644)

	// Complex content
	content := `package main

import (
	"fmt"
	"strings"
)

// GlobalVar is a variable.
var GlobalVar = "value"

const Pi = 3.14

// User is a struct.
type User struct {
	Name string
	age  int
}

// NewUser creates a user.
func NewUser(name string) *User {
	// Internal comment: setting name
	u := &User{Name: name}
	return u
}

// Greet greets.
func (u *User) Greet(msg string) string {
	fullMsg := fmt.Sprintf("%s, %s", msg, u.Name)
	return strings.ToUpper(fullMsg)
}

type Greeter interface {
	Greet(msg string) string
}
`
	filePath := filepath.Join(tmpDir, "main.go")
	os.WriteFile(filePath, []byte(content), 0644)

	// Execute Tool
	res, _, err := toolHandler(nil, nil, Params{File: filePath})
	if err != nil {
		t.Fatalf("toolHandler failed: %v", err)
	}
	if res.IsError {
		t.Fatalf("Tool returned error: %v", res.Content[0].(*mcp.TextContent).Text)
	}

	output := res.Content[0].(*mcp.TextContent).Text

	// Checks
	checks := []struct {
		desc     string
		contains string
		should   bool
	}{
		{"Package Decl", "package main", true},
		{"Imports", `import (
	"fmt"
	"strings"
)`, true},
		{"Global Var", `var GlobalVar = "value"`, true},
		{"Global Const", `const Pi = 3.14`, true},
		{"Type Struct", "type User struct {", true},
		{"Struct Field", "Name string", true},
		{"Func Signature", "func NewUser(name string) *User", true},
		{"Func Body", "u := &User{Name: name}", false}, // Should be removed
		{"Method Signature", "func (u *User) Greet(msg string) string", true},
		{"Method Body", "fmt.Sprintf", false},                         // Should be removed
		{"Internal Comment", "Internal comment: setting name", false}, // Should be removed
		{"Interface", "type Greeter interface", true},
		{"Doc Comment", "// NewUser creates a user.", true},
	}

	for _, check := range checks {
		has := strings.Contains(output, check.contains)
		if check.should && !has {
			t.Errorf("Missing %s: expected %q", check.desc, check.contains)
		} else if !check.should && has {
			t.Errorf("Unexpected %s: found %q", check.desc, check.contains)
		}
	}
}

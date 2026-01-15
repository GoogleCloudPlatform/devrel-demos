package master

import (
	"testing"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// TestCompileOnly ensures the package builds and types align.
// Real integration requires an API Key and making external calls, which we avoid in CI.
func TestRegister(t *testing.T) {
	s := mcp.NewServer(&mcp.Implementation{Name: "test", Version: "1.0"}, &mcp.ServerOptions{})

	updater := func(tools []string) error {
		return nil
	}

	Register(s, updater)
}

func TestFormatToolList(t *testing.T) {
	tools := []struct{ Name, Desc string }{
		{"toolA", "descA"},
		{"toolB", "descB"},
	}
	res := formatToolList(tools)
	expected := "- toolA: descA\n- toolB: descB\n"
	if res != expected {
		t.Errorf("Expected %q, got %q", expected, res)
	}
}

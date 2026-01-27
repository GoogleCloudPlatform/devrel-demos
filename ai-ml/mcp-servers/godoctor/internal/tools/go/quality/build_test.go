package quality

import (
	"context"
	"fmt"
	"strings"
	"testing"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

type mockRunner struct {
	outputs map[string]string
	errors  map[string]error
}

func (r *mockRunner) Run(ctx context.Context, dir, name string, args ...string) error {
	cmd := name + " " + strings.Join(args, " ")
	for k, v := range r.errors {
		if strings.Contains(cmd, k) {
			return v
		}
	}
	return nil
}

func (r *mockRunner) RunWithOutput(ctx context.Context, dir, name string, args ...string) (string, error) {
	cmd := name + " " + strings.Join(args, " ")
	output := ""
	for k, v := range r.outputs {
		if strings.Contains(cmd, k) {
			output = v
		}
	}
	
	var err error
	for k, v := range r.errors {
		if strings.Contains(cmd, k) {
			err = v
		}
	}
	return output, err
}

func (r *mockRunner) LookPath(file string) (string, error) {
	return "/usr/bin/" + file, nil
}

func TestHandler_Success(t *testing.T) {
	// Setup Mock
	oldRunner := CommandRunner
	defer func() { CommandRunner = oldRunner }()
	
	CommandRunner = &mockRunner{
		outputs: map[string]string{
			"go build": "",
			"go test":  "PASS",
		},
	}

	res, _, err := Handler(context.Background(), nil, Params{})
	if err != nil {
		t.Fatalf("Handler failed: %v", err)
	}
	if res.IsError {
		t.Error("Expected success, got error result")
	}
	
out := res.Content[0].(*mcp.TextContent).Text
	if !strings.Contains(out, "Build: ✅ PASS") {
		t.Errorf("Expected build success in output, got:\n%s", out)
	}
	if !strings.Contains(out, "Tests: ✅ PASS") {
		t.Errorf("Expected test success in output, got:\n%s", out)
	}
}

func TestHandler_BuildFail(t *testing.T) {
	// Setup Mock
	oldRunner := CommandRunner
	defer func() { CommandRunner = oldRunner }()
	
	CommandRunner = &mockRunner{
		outputs: map[string]string{
			"go build": "syntax error",
		},
		errors: map[string]error{
			"go build": fmt.Errorf("exit status 1"),
		},
	}

	res, _, _ := Handler(context.Background(), nil, Params{})
	
	if !res.IsError {
		t.Error("Expected error result for build failure")
	}
	
out := res.Content[0].(*mcp.TextContent).Text
	if !strings.Contains(out, "Build: ❌ FAILED") {
		t.Errorf("Expected build failure in output, got:\n%s", out)
	}
}